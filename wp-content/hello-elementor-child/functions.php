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

/**
 * Replace Add to Cart / Select Options text with a Cart Icon
 */
add_filter( 'woocommerce_loop_add_to_cart_link', 'hello_elementor_child_replace_add_to_cart_button', 10, 3 );
function hello_elementor_child_replace_add_to_cart_button( $link, $product, $args ) {
    $icon = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-shopping-cart"><circle cx="9" cy="21" r="1"></circle><circle cx="20" cy="21" r="1"></circle><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path></svg>';

    $link = sprintf(
        '<a href="%s" data-quantity="%s" class="%s" %s>%s</a>',
        esc_url( $product->add_to_cart_url() ),
        esc_attr( isset( $args['quantity'] ) ? $args['quantity'] : 1 ),
        esc_attr( isset( $args['class'] ) ? $args['class'] . ' custom-cart-icon-button' : 'button custom-cart-icon-button' ),
        isset( $args['attributes'] ) ? wc_implode_html_attributes( $args['attributes'] ) : '',
        $icon
    );

    return $link;
}
