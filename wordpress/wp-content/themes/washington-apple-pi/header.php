<?php
/**
 * Site header.
 *
 * @package Washington_Apple_Pi
 */
?><!DOCTYPE html>
<html <?php language_attributes(); ?>>
<head>
	<meta charset="<?php bloginfo( 'charset' ); ?>">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<?php wp_head(); ?>
</head>
<body <?php body_class(); ?>>
<?php wp_body_open(); ?>
<div class="wap-eval-banner" role="note">
	This is a WordPress evaluation preview of the Washington Apple Pi site, not the official site.
	<a href="https://www.theapplepi.org">Go to the official site</a>.
</div>
<header class="site-header">
	<div class="site-header-inner">
		<div class="site-branding">
			<?php if ( has_custom_logo() ) : ?>
				<?php the_custom_logo(); ?>
			<?php else : ?>
				<a class="custom-logo-link" href="<?php echo esc_url( home_url( '/' ) ); ?>">
					<img class="site-logo" src="<?php echo esc_url( get_template_directory_uri() . '/assets/logo.jpg' ); ?>" alt="THE PI">
				</a>
			<?php endif; ?>
		</div>
		<nav class="site-navigation" aria-label="Primary">
			<?php
			wp_nav_menu( array(
				'theme_location' => 'primary',
				'menu_class'     => 'primary-menu',
				'container'      => false,
				'fallback_cb'    => 'wp_page_menu',
				'depth'          => 2,
			) );
			?>
		</nav>
	</div>
</header>
