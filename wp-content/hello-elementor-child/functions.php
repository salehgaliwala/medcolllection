<?php
/**
 * Hello Elementor Child functions and definitions
 */

function hello_elementor_child_enqueue_styles() {
	wp_enqueue_style( 'parent-style', get_template_directory_uri() . '/style.css' );
	wp_enqueue_style( 'child-style', get_stylesheet_directory_uri() . '/style.css', array( 'parent-style' ), '1.0.0' );
}
add_action( 'wp_enqueue_scripts', 'hello_elementor_child_enqueue_styles' );

/**
 * Register Shop Sidebar
 */
function hello_elementor_child_register_sidebars() {
	register_sidebar( array(
		'name'          => 'Shop Sidebar',
		'id'            => 'shop-sidebar',
		'before_widget' => '<div id="%1$s" class="widget %2$s">',
		'after_widget'  => '</div>',
		'before_title'  => '<h2 class="widget-title">',
		'after_title'   => '</h2>',
	) );
}
add_action( 'widgets_init', 'hello_elementor_child_register_sidebars' );

/**
 * Limit products per page to show 3 rows.
 * Since we are targeting 3 columns (defined in CSS), 3 rows = 9 products.
 */
add_filter( 'loop_shop_per_page', 'hello_elementor_child_products_per_page', 20 );
function hello_elementor_child_products_per_page( $cols ) {
    return 9;
}
