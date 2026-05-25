<?php
/**
 * The Template for displaying all product archives, including the main shop page which is a post type archive
 *
 * This template can be overridden by copying it to yourtheme/woocommerce/archive-product.php.
 *
 * @see https://woocommerce.com/document/template-structure/
 * @package WooCommerce\Templates
 * @version 8.6.0
 */

defined( 'ABSPATH' ) || exit;

get_header( 'shop' );

/**
 * Hook: woocommerce_before_main_content.
 *
 * @hooked woocommerce_output_content_wrapper - 10 (outputs opening divs for the content)
 * @hooked woocommerce_breadcrumb - 20
 * @hooked WC_Structured_Data::generate_product_data_json - 30
 */
do_action( 'woocommerce_before_main_content' );

?>
<header class="woocommerce-products-header">
	<?php if ( apply_filters( 'woocommerce_show_page_title', true ) ) : ?>
		<h1 class="woocommerce-products-header__title page-title"><?php woocommerce_page_title(); ?></h1>
	<?php endif; ?>

	<?php
	/**
	 * Hook: woocommerce_archive_description.
	 *
	 * @hooked woocommerce_taxonomy_archive_description - 10
	 * @hooked woocommerce_product_archive_description - 10
	 */
	do_action( 'woocommerce_archive_description' );
	?>
</header>

<div class="shop-container">
    <aside class="shop-sidebar">
        <?php
        /**
         * Hook: woocommerce_sidebar.
         *
         * @hooked woocommerce_get_sidebar - 10
         */
        // Instead of standard sidebar, we ensure categories and brands are visible as requested
        if ( is_active_sidebar( 'shop-sidebar' ) ) {
            dynamic_sidebar( 'shop-sidebar' );
        } else {
            // Fallback: Display categories and brands if sidebar is empty
            echo '<div class="widget widget_product_categories"><h2>Categories</h2>';
            wp_list_categories( array( 'taxonomy' => 'product_cat', 'title_li' => '' ) );
            echo '</div>';

            echo '<div class="widget widget_product_brands"><h2>Brands</h2>';
            // Assuming brands are in pa_merk attribute as found in exploration
            $brands = get_terms( array( 'taxonomy' => 'pa_merk', 'hide_empty' => false ) );
            if ( ! is_wp_error( $brands ) && ! empty( $brands ) ) {
                echo '<ul>';
                foreach ( $brands as $brand ) {
                    echo '<li><a href="' . esc_url( get_term_link( $brand ) ) . '">' . esc_html( $brand->name ) . '</a></li>';
                }
                echo '</ul>';
            }
            echo '</div>';
        }
        ?>
    </aside>

    <div class="shop-content-area">
        <div class="shop-top-bar">
            <?php
            /**
             * Hook: woocommerce_before_shop_loop.
             *
             * @hooked woocommerce_output_all_notices - 10
             * @hooked woocommerce_result_count - 20
             * @hooked woocommerce_catalog_ordering - 30
             */
            do_action( 'woocommerce_before_shop_loop' );
            ?>
        </div>

        <?php
        if ( woocommerce_product_loop() ) {

            woocommerce_product_loop_start();

            if ( wc_get_loop_prop( 'total' ) ) {
                while ( have_posts() ) {
                    the_post();

                    /**
                     * Hook: woocommerce_shop_loop.
                     */
                    do_action( 'woocommerce_shop_loop' );

                    wc_get_template_part( 'content', 'product' );
                }
            }

            woocommerce_product_loop_end();

            /**
             * Hook: woocommerce_after_shop_loop.
             *
             * @hooked woocommerce_pagination - 10
             */
            do_action( 'woocommerce_after_shop_loop' );
        } else {
            /**
             * Hook: woocommerce_no_products_found.
             *
             * @hooked wc_no_products_found - 10
             */
            do_action( 'woocommerce_no_products_found' );
        }
        ?>
    </div>
</div>

<?php
/**
 * Hook: woocommerce_after_main_content.
 *
 * @hooked woocommerce_output_content_wrapper_end - 10 (outputs closing divs for the content)
 */
do_action( 'woocommerce_after_main_content' );

/**
 * Hook: woocommerce_sidebar.
 *
 * @hooked woocommerce_get_sidebar - 10
 */
// do_action( 'woocommerce_sidebar' ); // Removed standard sidebar from bottom

get_footer( 'shop' );
