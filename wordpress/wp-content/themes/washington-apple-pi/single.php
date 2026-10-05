<?php
/**
 * Single blog post.
 *
 * @package Washington_Apple_Pi
 */

get_header();
?>
<main id="primary" class="site-main">
	<?php
	while ( have_posts() ) :
		the_post();
		?>
		<article <?php post_class(); ?>>
			<header class="entry-header">
				<h1><?php the_title(); ?></h1>
				<p class="entry-date"><?php echo esc_html( get_the_date() ); ?></p>
			</header>
			<div class="entry-content">
				<?php the_content(); ?>
			</div>
			<?php
			if ( comments_open() || get_comments_number() ) {
				comments_template();
			}
			?>
		</article>
		<?php
	endwhile;
	?>
</main>
<?php
get_footer();
