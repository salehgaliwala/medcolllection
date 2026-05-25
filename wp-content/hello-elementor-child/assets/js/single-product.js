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
});
