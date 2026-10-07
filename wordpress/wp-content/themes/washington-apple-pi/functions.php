<?php
/**
 * Washington Apple Pi theme setup.
 *
 * @package Washington_Apple_Pi
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

function wap_setup() {
	add_theme_support( 'title-tag' );
	add_theme_support( 'custom-logo', array(
		'height'      => 80,
		'width'       => 360,
		'flex-height' => true,
		'flex-width'  => true,
	) );
	add_theme_support( 'post-thumbnails' );
	add_theme_support( 'responsive-embeds' );
	add_theme_support( 'html5', array( 'search-form', 'comment-form', 'comment-list', 'gallery', 'caption', 'style', 'script' ) );
	add_theme_support( 'wp-block-styles' );
	add_editor_style( 'style.css' );

	register_nav_menus( array(
		'primary' => 'Primary',
	) );
}
add_action( 'after_setup_theme', 'wap_setup' );

function wap_assets() {
	wp_enqueue_style(
		'wap-fonts',
		'https://fonts.googleapis.com/css2?family=Maven+Pro:wght@400;600;700&display=swap',
		array(),
		null
	);
	wp_enqueue_style( 'wap-style', get_stylesheet_uri(), array( 'wap-fonts' ), '1.0.0' );
}
add_action( 'wp_enqueue_scripts', 'wap_assets' );

function wap_editor_fonts() {
	wp_enqueue_style(
		'wap-editor-fonts',
		'https://fonts.googleapis.com/css2?family=Maven+Pro:wght@400;600;700&display=swap',
		array(),
		null
	);
}
add_action( 'enqueue_block_editor_assets', 'wap_editor_fonts' );

/**
 * The contact form is only a picture of the fields. It does not send mail.
 */
function wap_mark_contact_form( $content ) {
	if ( false === strpos( $content, 'wap-contact-form' ) ) {
		return $content;
	}
	$note = '<p class="wap-form-disabled" role="note"><strong>This form does not send email.</strong> It is part of the evaluation preview and is not connected to Washington Apple Pi. Nothing typed here is delivered.</p>';
	$content = str_replace(
		'<form class="wap-contact-form"',
		$note . '<form class="wap-contact-form"',
		$content
	);
	$content = str_replace(
		'<button type="button">Submit</button>',
		'<button type="button" disabled>Submit</button>',
		$content
	);
	return $content;
}
add_filter( 'the_content', 'wap_mark_contact_form', 20 );
