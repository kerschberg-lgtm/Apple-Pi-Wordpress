<?php
/**
 * Point imported content at files in the media library.
 *
 * The WXR keeps the original theapplepi.org URLs so any WordPress importer
 * can download them. After import, each attachment has _wap_source_url.
 * This replaces those URLs in pages and posts with the local file URL.
 */

$attachments = get_posts(
	array(
		'post_type'      => 'attachment',
		'post_status'    => 'inherit',
		'posts_per_page' => -1,
	)
);

$map = array();
foreach ( $attachments as $attachment ) {
	$source = get_post_meta( $attachment->ID, '_wap_source_url', true );
	$local  = wp_get_attachment_url( $attachment->ID );
	if ( ! $source || ! $local ) {
		continue;
	}
	$map[ $source ] = $local;
	$bare = preg_replace( '/\?.*$/', '', $source );
	if ( $bare && ! isset( $map[ $bare ] ) ) {
		$map[ $bare ] = $local;
	}
}

uksort(
	$map,
	static function ( $a, $b ) {
		return strlen( $b ) - strlen( $a );
	}
);

$updated = 0;
$posts   = get_posts(
	array(
		'post_type'      => array( 'page', 'post' ),
		'post_status'    => 'any',
		'posts_per_page' => -1,
	)
);

foreach ( $posts as $post ) {
	$content = $post->post_content;
	$new     = strtr( $content, $map );
	if ( $new !== $content ) {
		wp_update_post(
			array(
				'ID'           => $post->ID,
				'post_content' => $new,
			)
		);
		$updated++;
	}
}

echo 'Remapped ' . count( $map ) . " media URLs in {$updated} posts.\n";
