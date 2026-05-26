<?php
/**
 * Hello Elementor Child functions and definitions
 */

function hello_elementor_child_enqueue_styles() {
	wp_enqueue_style( 'parent-style', get_template_directory_uri() . '/style.css' );
	wp_enqueue_style( 'child-style', get_stylesheet_directory_uri() . '/style.css', array( 'parent-style' ), '1.0.0' );

    if ( is_product() ) {
        wp_enqueue_script( 'feather-icons', 'https://cdn.jsdelivr.net/npm/feather-icons/dist/feather.min.js', array(), '4.29.0', true );
        wp_enqueue_script( 'hello-elementor-child-single-product', get_stylesheet_directory_uri() . '/assets/js/single-product.js', array( 'jquery', 'feather-icons' ), '1.0.0', true );
    }
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
 * Reorder Single Product Summary
 * Order: Title (5), Short Description (10), Price (15), Variations/Add to Cart (20)
 */
remove_action( 'woocommerce_single_product_summary', 'woocommerce_template_single_title', 5 );
remove_action( 'woocommerce_single_product_summary', 'woocommerce_template_single_rating', 10 );
remove_action( 'woocommerce_single_product_summary', 'woocommerce_template_single_price', 10 );
remove_action( 'woocommerce_single_product_summary', 'woocommerce_template_single_excerpt', 20 );
remove_action( 'woocommerce_single_product_summary', 'woocommerce_template_single_add_to_cart', 30 );
remove_action( 'woocommerce_single_product_summary', 'woocommerce_template_single_meta', 40 );
remove_action( 'woocommerce_single_product_summary', 'woocommerce_template_single_sharing', 50 );

add_action( 'woocommerce_single_product_summary', 'woocommerce_template_single_title', 5 );
add_action( 'woocommerce_single_product_summary', 'woocommerce_template_single_excerpt', 10 );
add_action( 'woocommerce_single_product_summary', 'woocommerce_template_single_price', 15 );
add_action( 'woocommerce_single_product_summary', 'woocommerce_template_single_add_to_cart', 20 );
add_action( 'woocommerce_single_product_summary', 'woocommerce_template_single_meta', 30 );

/**
 * Convert Variations Dropdown to Button Selection
 */
add_filter( 'woocommerce_dropdown_variation_attribute_options_html', 'hello_elementor_child_variation_buttons', 10, 2 );
function hello_elementor_child_variation_buttons( $html, $args ) {
    $options   = $args['options'];
    $product   = $args['product'];
    $attribute = $args['attribute'];
    $name      = $args['name'] ? $args['name'] : 'attribute_' . sanitize_title( $attribute );
    $id        = $args['id'] ? $args['id'] : sanitize_title( $attribute );
    $class     = $args['class'];

    if ( empty( $options ) || ! $product ) {
        return $html;
    }

    $buttons_html = '<div class="variation-buttons" data-attribute_name="attribute_' . esc_attr( sanitize_title( $attribute ) ) . '">';

    foreach ( $options as $option ) {
        $selected = ( $args['selected'] === $option ) ? 'selected' : '';
        $buttons_html .= sprintf(
            '<button type="button" class="variation-button %s" data-value="%s">%s</button>',
            $selected,
            esc_attr( $option ),
            esc_html( apply_filters( 'woocommerce_variation_option_name', $option ) )
        );
    }

    $buttons_html .= '</div>';

    // Keep the original hidden select for WooCommerce core JS compatibility
    $html = '<div class="hidden-variation-select" style="display:none;">' . $html . '</div>' . $buttons_html;

    return $html;
}

/**
 * Vertical Thumbnails for Single Product
 */
add_filter( 'woocommerce_single_product_image_gallery_classes', 'hello_elementor_child_vertical_thumbnails' );
function hello_elementor_child_vertical_thumbnails( $classes ) {
    $classes[] = 'vertical-thumbnails';
    return $classes;
}

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

/**
 * Custom Product Tabs
 */
add_filter( 'woocommerce_product_tabs', 'hello_elementor_child_custom_product_tabs', 98 );
function hello_elementor_child_custom_product_tabs( $tabs ) {
    // Rename Additional Information to Specification
    if ( isset( $tabs['additional_information'] ) ) {
        $tabs['additional_information']['title'] = __( 'Specification', 'woocommerce' );
        $tabs['additional_information']['callback'] = 'hello_elementor_child_specification_tab_content';
        $tabs['additional_information']['priority'] = 5;
    }

    // Reorder Description
    if ( isset( $tabs['description'] ) ) {
        $tabs['description']['priority'] = 10;
    }

    // Reorder Reviews
    if ( isset( $tabs['reviews'] ) ) {
        $tabs['reviews']['priority'] = 15;
    }

    return $tabs;
}

/**
 * Specification Tab Content (3 columns with icons)
 */
function hello_elementor_child_specification_tab_content() {
    global $product;

    // Map common attribute names/labels to icons
    $specs = array(
        'size'  => array( 'label' => __( 'Size', 'woocommerce' ), 'icon' => 'maximize', 'value' => '' ),
        'color' => array( 'label' => __( 'Colour', 'woocommerce' ), 'icon' => 'palette', 'value' => '' ),
        'brand' => array( 'label' => __( 'Brand', 'woocommerce' ), 'icon' => 'tag', 'value' => '' ),
    );

    $all_attributes = $product->get_attributes();

    foreach ( $all_attributes as $attribute ) {
        $name = strtolower( $attribute->get_name() );
        $label = wc_attribute_label( $attribute->get_name() );
        $value = $product->get_attribute( $attribute->get_name() );

        if ( strpos( $name, 'maat' ) !== false || strpos( strtolower($label), 'size' ) !== false || strpos( strtolower($label), 'maat' ) !== false ) {
            $specs['size']['value'] = $value;
        } elseif ( strpos( $name, 'kleur' ) !== false || strpos( strtolower($label), 'color' ) !== false || strpos( strtolower($label), 'kleur' ) !== false ) {
            $specs['color']['value'] = $value;
        } elseif ( strpos( $name, 'merk' ) !== false || strpos( strtolower($label), 'brand' ) !== false || strpos( strtolower($label), 'merk' ) !== false ) {
            $specs['brand']['value'] = $value;
        }
    }

    echo '<div class="product-specifications-grid">';

    foreach ( $specs as $key => $data ) {
        if ( ! empty( $data['value'] ) ) {
            echo '<div class="spec-column">';
            echo '<div class="spec-icon"><i data-feather="' . esc_attr( $data['icon'] ) . '"></i></div>';
            echo '<div class="spec-info">';
            echo '<strong>' . esc_html( $data['label'] ) . '</strong>';
            echo '<span>' . esc_html( $data['value'] ) . '</span>';
            echo '</div>';
            echo '</div>';
        }
    }

    echo '</div>';
}
