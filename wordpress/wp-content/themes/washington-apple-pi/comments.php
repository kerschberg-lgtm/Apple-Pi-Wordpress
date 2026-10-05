<?php
/**
 * Comments, including the public comments captured from the blog.
 *
 * @package Washington_Apple_Pi
 */

if ( post_password_required() ) {
	return;
}
?>
<section class="comments-area">
	<?php if ( have_comments() ) : ?>
		<h2><?php comments_number( 'Comments', '1 Comment', '% Comments' ); ?></h2>
		<ol class="comment-list">
			<?php
			wp_list_comments( array(
				'style'       => 'ol',
				'short_ping'  => true,
				'avatar_size' => 0,
			) );
			?>
		</ol>
	<?php endif; ?>
	<?php
	if ( comments_open() ) {
		comment_form();
	} elseif ( get_comments_number() ) {
		echo '<p>Comments are closed.</p>';
	}
	?>
</section>
