<?php
/**
 * Load the WXR into this WordPress site using files from the capture.
 *
 * The container that runs the preview may not be allowed to download from
 * the public web. Pages and posts still come from washington-apple-pi.wxr.
 * Images and the bylaws PDF are copied from the captured files listed in
 * media-map.json.
 */

if ( get_option( 'wap_content_imported' ) ) {
	echo "Content is already imported.\n";
	return;
}

$admin = get_user_by( 'login', 'pi-admin' );
if ( $admin ) {
	wp_set_current_user( $admin->ID );
}
kses_remove_filters();

$wxr_path = '/import/washington-apple-pi.wxr';
$map_path = '/import/media-map.json';

if ( ! file_exists( $wxr_path ) || ! file_exists( $map_path ) ) {
	echo "Missing import files.\n";
	exit( 1 );
}

$media_map = json_decode( file_get_contents( $map_path ), true );
if ( ! is_array( $media_map ) ) {
	echo "Could not read media map.\n";
	exit( 1 );
}

$xml = simplexml_load_file( $wxr_path );
if ( ! $xml ) {
	echo "Could not read the WXR file.\n";
	exit( 1 );
}

require_once ABSPATH . 'wp-admin/includes/image.php';
require_once ABSPATH . 'wp-admin/includes/file.php';
require_once ABSPATH . 'wp-admin/includes/media.php';

$wp_ns      = 'http://wordpress.org/export/1.2/';
$content_ns = 'http://purl.org/rss/1.0/modules/content/';

$id_map   = array();
$url_map  = array();
$items    = array();

foreach ( $xml->channel->item as $item ) {
	$wp      = $item->children( $wp_ns );
	$content = $item->children( $content_ns );
	$meta    = array();
	foreach ( $wp->postmeta as $row ) {
		$meta[ (string) $row->meta_key ] = (string) $row->meta_value;
	}
	$comments = array();
	foreach ( $wp->comment as $comment ) {
		$comments[] = $comment;
	}
	$items[] = array(
		'item'     => $item,
		'wp'       => $wp,
		'content'  => (string) $content->encoded,
		'meta'     => $meta,
		'comments' => $comments,
		'type'     => (string) $wp->post_type,
		'old_id'   => (int) $wp->post_id,
	);
}

function wap_replace_urls( $content, $url_map ) {
	if ( ! $content || ! $url_map ) {
		return $content;
	}
	uksort(
		$url_map,
		static function ( $a, $b ) {
			return strlen( $b ) - strlen( $a );
		}
	);
	return strtr( $content, $url_map );
}

$upload = wp_upload_dir();
$copied = 0;
$missed = 0;

foreach ( $items as $entry ) {
	if ( 'attachment' !== $entry['type'] ) {
		continue;
	}
	$source = $entry['meta']['_wap_source_url'] ?? '';
	if ( ! $source && isset( $entry['wp']->attachment_url ) ) {
		$source = (string) $entry['wp']->attachment_url;
	}
	$rel = $media_map[ $source ] ?? '';
	$local = $rel ? '/capture/' . ltrim( $rel, '/' ) : '';
	if ( ! $source || ! $local || ! file_exists( $local ) ) {
		echo "Missing file for {$source}\n";
		$missed++;
		continue;
	}
	$filename = wp_unique_filename( $upload['path'], basename( parse_url( $source, PHP_URL_PATH ) ) );
	$dest     = trailingslashit( $upload['path'] ) . $filename;
	if ( ! copy( $local, $dest ) ) {
		echo "Could not copy {$local}\n";
		$missed++;
		continue;
	}
	$filetype = wp_check_filetype( $filename );
	$attach_id = wp_insert_attachment(
		array(
			'post_mime_type' => $filetype['type'],
			'post_title'     => (string) $entry['item']->title,
			'post_status'    => 'inherit',
			'guid'           => trailingslashit( $upload['url'] ) . $filename,
		),
		$dest
	);
	if ( is_wp_error( $attach_id ) || ! $attach_id ) {
		echo "Could not attach {$filename}\n";
		$missed++;
		continue;
	}
	$metadata = wp_generate_attachment_metadata( $attach_id, $dest );
	wp_update_attachment_metadata( $attach_id, $metadata );
	update_post_meta( $attach_id, '_wap_source_url', $source );
	$id_map[ $entry['old_id'] ] = $attach_id;
	$local_url = wp_get_attachment_url( $attach_id );
	$url_map[ $source ] = $local_url;
	$bare = preg_replace( '/\?.*$/', '', $source );
	if ( $bare && ! isset( $url_map[ $bare ] ) ) {
		$url_map[ $bare ] = $local_url;
	}
	$copied++;
}

echo "Copied {$copied} media files ({$missed} missing).\n";

foreach ( $items as $entry ) {
	if ( ! in_array( $entry['type'], array( 'page', 'post' ), true ) ) {
		continue;
	}
	$wp = $entry['wp'];
	$new_id = wp_insert_post(
		array(
			'post_type'      => $entry['type'],
			'post_status'    => (string) $wp->status ?: 'publish',
			'post_title'     => (string) $entry['item']->title,
			'post_name'      => (string) $wp->post_name,
			'post_content'   => wap_replace_urls( $entry['content'], $url_map ),
			'post_date'      => (string) $wp->post_date,
			'post_date_gmt'  => (string) $wp->post_date_gmt,
			'comment_status' => (string) $wp->comment_status ?: 'closed',
			'ping_status'    => 'closed',
		),
		true
	);
	if ( is_wp_error( $new_id ) ) {
		echo 'Failed ' . $entry['type'] . ' ' . (string) $entry['item']->title . ': ' . $new_id->get_error_message() . "\n";
		continue;
	}
	$id_map[ $entry['old_id'] ] = $new_id;
	foreach ( $entry['comments'] as $comment ) {
		wp_insert_comment(
			array(
				'comment_post_ID'  => $new_id,
				'comment_author'   => (string) $comment->comment_author,
				'comment_content'  => (string) $comment->comment_content,
				'comment_date'     => (string) $comment->comment_date,
				'comment_date_gmt' => (string) $comment->comment_date_gmt,
				'comment_approved' => (string) $comment->comment_approved,
				'comment_type'     => (string) $comment->comment_type,
			)
		);
	}
	echo ucfirst( $entry['type'] ) . ': ' . (string) $entry['item']->title . "\n";
}

$menu_id = wp_create_nav_menu( 'Primary' );
if ( is_wp_error( $menu_id ) ) {
	echo 'Menu: ' . $menu_id->get_error_message() . "\n";
	$menu_id = 0;
}

$menu_item_map = array();
if ( $menu_id ) {
	foreach ( $items as $entry ) {
		if ( 'nav_menu_item' !== $entry['type'] ) {
			continue;
		}
		$meta   = $entry['meta'];
		$type   = $meta['_menu_item_type'] ?? 'custom';
		$parent = (int) ( $meta['_menu_item_menu_item_parent'] ?? 0 );
		$args   = array(
			'menu-item-title'     => (string) $entry['item']->title,
			'menu-item-status'    => 'publish',
			'menu-item-position'  => (int) $entry['wp']->menu_order,
			'menu-item-parent-id' => $parent && isset( $menu_item_map[ $parent ] ) ? $menu_item_map[ $parent ] : 0,
		);
		if ( 'post_type' === $type ) {
			$old_object = (int) ( $meta['_menu_item_object_id'] ?? 0 );
			$args['menu-item-type']      = 'post_type';
			$args['menu-item-object']    = 'page';
			$args['menu-item-object-id'] = $id_map[ $old_object ] ?? 0;
		} else {
			$args['menu-item-type'] = 'custom';
			$args['menu-item-url']  = $meta['_menu_item_url'] ?? '#';
		}
		$new_item = wp_update_nav_menu_item( $menu_id, 0, $args );
		if ( ! is_wp_error( $new_item ) ) {
			$menu_item_map[ $entry['old_id'] ] = $new_item;
		}
	}
	$locations            = get_theme_mod( 'nav_menu_locations', array() );
	$locations['primary'] = $menu_id;
	set_theme_mod( 'nav_menu_locations', $locations );
	echo "Menu assigned (" . count( $menu_item_map ) . " items).\n";
}

echo "Done.\n";
