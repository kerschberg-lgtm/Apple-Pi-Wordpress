<?php
/**
 * Site footer. Wording follows the public site footer.
 *
 * @package Washington_Apple_Pi
 */
?>
<footer class="site-footer">
	<div class="site-footer-inner">
		<div>
			<h2>Follow us on:</h2>
			<ul class="social-links">
				<li><a href="https://www.facebook.com/washingtonapplepi" target="_blank" rel="noopener noreferrer">Facebook</a></li>
				<li><a href="https://www.youtube.com/@WashingtonApplePi" target="_blank" rel="noopener noreferrer">YouTube</a></li>
				<li><a href="https://twitter.com/Pi_org" target="_blank" rel="noopener noreferrer">Twitter</a></li>
				<li><a href="mailto:office@wap.org">Email</a></li>
			</ul>
		</div>
		<div>
			<p>To message us about membership or with other questions, contact us here:<br>
			<strong><a href="<?php echo esc_url( home_url( '/contact-us/' ) ); ?>">www.theapplepi.org/contact.html</a></strong></p>
			<p>Click here for information on <strong><a href="<?php echo esc_url( home_url( '/the-pi-board/' ) ); ?>">Pi Governance</a></strong>.</p>
		</div>
	</div>
</footer>
<?php wp_footer(); ?>
</body>
</html>
