<?php
/**
 * Blog index.
 *
 * @package Washington_Apple_Pi
 */

get_header();
?>
<main id="primary" class="site-main">
	<header class="entry-header">
		<h1>Blog</h1>
	</header>
	<?php if ( have_posts() ) : ?>
		<div class="posts-list">
			<?php
			while ( have_posts() ) :
				the_post();
				?>
				<article <?php post_class(); ?>>
					<h2><a href="<?php the_permalink(); ?>"><?php the_title(); ?></a></h2>
					<p class="post-date"><?php echo esc_html( get_the_date() ); ?></p>
					<div class="entry-content"><?php the_content(); ?></div>
				</article>
				<?php
			endwhile;
			?>
		</div>
		<?php the_posts_pagination(); ?>
	<?php else : ?>
		<p>No posts yet.</p>
	<?php endif; ?>
</main>
<?php
get_footer();
