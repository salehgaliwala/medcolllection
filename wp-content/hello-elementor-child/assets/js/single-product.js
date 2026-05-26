jQuery(document).ready(function($) {
    // Variation Button Click
    $(document).on('click', '.variation-button', function(e) {
        e.preventDefault();
        var $button = $(this);
        var value = $button.data('value');
        var $wrapper = $button.closest('.variation-buttons');
        var attributeName = $wrapper.data('attribute_name');

        // Update Buttons
        $wrapper.find('.variation-button').removeClass('selected');
        $button.addClass('selected');

        // Update Hidden Select
        var $form = $button.closest('form.variations_form');
        var $select = $form.find('select[name="' + attributeName + '"]');
        $select.val(value).trigger('change');
    });

    // Reset buttons when variations are reset
    $(document).on('reset_data', 'form.variations_form', function() {
        $('.variation-button').removeClass('selected');
    });

    // Initialize Feather Icons
    if (typeof feather !== 'undefined') {
        feather.replace();
    }

    // Product Accordion/Toggle
    $(document).on('click', '.accordion-header', function(e) {
        e.preventDefault();
        var $item = $(this).closest('.accordion-item');
        var $content = $item.find('.accordion-content');

        $content.slideToggle(300);
        $item.toggleClass('active');

        // Close other items (optional, make it true accordion)
        $item.siblings().removeClass('active').find('.accordion-content').slideUp(300);
    });
});
