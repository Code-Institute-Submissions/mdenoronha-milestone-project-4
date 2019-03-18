// For document.ready
$(document).ready(function() {
    $('.modal').modal();
    $('.dropdown-trigger').dropdown();
    $('.carousel').carousel({
        dist: 0,
        padding: 50,
        noWrap: true,
    });
    $('.sidenav').sidenav();
    $('.fixed-action-btn').floatingActionButton();
    $('.collapsible').collapsible();
    $('select').formSelect();
    $('.materialboxed').materialbox();
});

// My account
function account_details_change() {
    $('.account-details-submit').removeClass('disabled')
    $('.account-changes-message').removeClass('hidden')
    $('.account-changes-message').removeClass('hidden-opacity')
    $('#current-password').removeAttr('disabled')
}

$('.edit-last-name').on('click', function() {
    $('#last-name').removeAttr('disabled')
    account_details_change()
})

$('.edit-first-name').on('click', function() {
    $('#first-name').removeAttr('disabled')
    account_details_change()
})

$('.edit-username').on('click', function() {
    $('#username').removeAttr('disabled')
    account_details_change()
})

$('.edit-password').on('click', function() {
    $('#password').removeAttr('disabled')
    account_details_change()
})

var elem = $(".autocomplete")

$('.autocomplete').on('input', function() {
    if ($(this).val() != "") {
        $('.search-button').addClass('active-button')
    }
    else {
        $('.search-button').removeClass('active-button')
    }
})



$("body").on('DOMSubtreeModified', elem, function() {
    if ($('ul.autocomplete-content li').length >= 1) {
        if ($('ul.autocomplete-content p:first').attr("id") != "featured-heading") {
            $('.autocomplete-content').prepend('<p class="unselectable" id="featured-heading">MOST POPULAR RECIPES</p>')
        }

    }
});

// Search Page

if ($('#serves-slider')[0]) {
    var data_element = $('#search-data-set')

    var default_filters = true
    var serves_slider_noUiSlider = noUiSlider.create($('#serves-slider')[0], {
        start: [1, 6],
        connect: true,
        step: 1,
        range: {
            'min': 1,
            'max': 6
        },
        ariaFormat: wNumb({
            decimals: 0
        }),
        format: wNumb({
            decimals: 0,

        })
    });

    var serves_slider = $('#serves-slider')[0];
    var serves_slider_value = $('#serves-slider-value')[0];

    serves_slider.noUiSlider.set([
        data_element.data("lower-slider-serves"),
        data_element.data("upper-slider-serves")
    ])

    $("#serves-slider-value-input").val(serves_slider_noUiSlider.get());

    serves_slider_noUiSlider.on("change", function() {
        $("#serves-slider-value-input").val(serves_slider_noUiSlider.get());
    });


    serves_slider.noUiSlider.on('update', function(values) {
        serves_slider_value.innerHTML = values.join(' - ');
    });

    var time_slider_noUiSlider = noUiSlider.create($('#time-slider')[0], {
        start: [10, 180],
        connect: true,
        step: 10,
        range: {
            'min': 10,
            'max': 180
        },
        ariaFormat: wNumb({
            decimals: 0
        }),
        format: wNumb({
            decimals: 0,

        })
    });

    var time_slider = $('#time-slider')[0];
    var time_slider_value = $('#time-slider-value')[0];

    time_slider.noUiSlider.set([
        data_element.data("lower-slider-time"),
        data_element.data("upper-slider-time")
    ])

    $("#time-slider-value-input").val(time_slider_noUiSlider.get());

    time_slider_noUiSlider.on("change", function() {
        $("#time-slider-value-input").val(time_slider_noUiSlider.get());
    });

    time_slider.noUiSlider.on('update', function(values) {
        time_slider_value.innerHTML = values.join(' - ');
    });

    var chips_data = data_element.data("chips")

    var chips_split = chips_data.split(",")
    var chips_array = []
    if (chips_data) {
        for (i = 0; i < chips_split.length; i++) {
            temp_object = { tag: chips_split[i] }
            chips_array.push(temp_object)
        }
    }

    $('.ingredients-chips').chips({
        placeholder: 'e.g. Chicken',
        // data_element.data("chips")
        data: chips_array,
        // Syntax below is wrong, improve?
        onChipAdd: function() {
            if_default()
            var ingredients_chips_instance = M.Chips.getInstance($('.ingredients-chips'))
            var ingredients_chips_object = ingredients_chips_instance.chipsData

            $(".ingredient-warning-message").addClass('hidden')

            for (key in ingredients_chips_object) {
                var value = ingredients_chips_object[key]['tag'];
                if (/[^a-zA-Z ]/.test(value)) {
                    ingredients_chips_instance.deleteChip(key);
                    $(".ingredient-warning-message").removeClass('hidden')
                }

            }
            update_ingredients_input()
            if_default()
        },
        onChipDelete: function() {
            update_ingredients_input()
            if_default()
        }
    });

    function update_ingredients_input() {
        var ingredients_chips_instance = M.Chips.getInstance($('.ingredients-chips'));
        var chips = [];
        for (key in ingredients_chips_instance.chipsData) {
            var value = ingredients_chips_instance.chipsData[key]['tag'];
            chips.push(value)
        }
        $('#ingredients-chips-value-input').val(chips)
    }

    update_ingredients_input()

    function if_default() {
        if ($('#ingredients-chips-value-input').val() == "" &&
            !$(".vegan").is(':checked') &&
            !$(".vegetarian").is(':checked') &&
            !$(".gluten-free").is(':checked') &&
            $(".easy").is(':checked') &&
            $(".medium").is(':checked') &&
            $(".hard").is(':checked') &&
            $("#serves-slider-value-input").val() == "1,6" &&
            $("#time-slider-value-input").val() == "10,180") {
            $('.reset-filters').removeClass("active-reset-filters")
        }
        else {
            $('.reset-filters').addClass("active-reset-filters")
            $('.collapsible-body').css('display', 'block')
            $('.filter-column li').addClass('active')
        }
    }

    if_default()

    $(".master-filter").on("change", function() {
        if_default()
    })

    $('.time-type').on('click', function() {
        if_default()
    });

    $('.serves-type').on('click', function() {
        if_default()
    });

    $('.reset-filters').on('click', function() {
        $('#ingredients-chips-value-input').val("")
        $('.vegan').prop('checked', false);
        $('.vegetarian').prop('checked', false);
        $('.gluten-free').prop('checked', false);
        $('.easy').prop('checked', true);
        $('.medium').prop('checked', true);
        $('.hard').prop('checked', true);
        $("#serves-slider-value-input").val("1,6")
        $('#serves-slider')[0].noUiSlider.set([1, 6])
        $("#time-slider-value-input").val("10,180")
        $('#time-slider')[0].noUiSlider.set([10, 180])

        var ingredients = M.Chips.getInstance($(".ingredients-chips"))
        var ingredients_length = ingredients.chipsData.length
        console.log(ingredients_length)
        for (i = 0; i < ingredients_length; i++) {
            ingredients.deleteChip(ingredients_length - 1 - i)
        }
        if_default()
    })

    $(".vegan").change(function() {
        if (this.checked) {
            $(".vegetarian").prop("checked", true)
        }
    })

    $(".vegetarian").change(function() {
        if ($(".vegan").is(':checked')) {
            $(".vegan").prop("checked", false)
        }
    })

    var $window = $(window)

    function resize() {
        if ($window.width() < 600) {
            $('.collapsible-header').removeClass('hidden');
            return $('.filter-body').addClass('collapsible-body');
        }

        $('.filter-body').removeClass('collapsible-body');
        $('.collapsible-header').addClass('hidden');
    }

    $window
        .resize(resize)
        .trigger('resize');

}

// Homepage

var data_element_index = $('#index-data-set').data("autocompleteRecipe")

$('input.autocomplete').autocomplete({
    data: data_element_index,
    limit: 7,
    onAutocomplete: function(val) {
        //   Callback function when value is autcompleted.
        var val2 = val.replace(/ /g, "-");
        window.open('/recipe/' + val2 + "/" + data_element_index[val], "_self");
    }
});

// Change recipe info

$(".change-recipe-image").on('click', function() {
    if ($(".input-recipe-image").hasClass(("hidden"))) {
        $(this).html("Cancel");
        $(".input-recipe-image").removeClass("hidden");
        $(".update-recipe-image").addClass("hidden");
    }
    else {
        $(this).html("Change Image");
        $(".file-path").val("").removeClass('valid');
        $("#file-input").val("");
        $(".input-recipe-image").addClass("hidden");
        $(".input-recipe-image").val('');
        $(".update-recipe-image").removeClass("hidden");
    }
})

// Add recipe info

$('select[name="serves"]').on('change', function() {
    $('.input-field.serves input').addClass('valid-input')
    $('.input-field.serves label').addClass('valid-label')
})

$('select[name="difficulty"]').on('change', function() {
    $('.input-field.difficulty input').addClass('valid-input')
    $('.input-field.difficulty label').addClass('valid-label')
})

$('select[name="time"]').on('change', function() {
    $('.input-field.time input').addClass('valid-input')
    $('.input-field.time label').addClass('valid-label')
})

$('textarea').on('change', function() {
    $(this).addClass('valid')
})

$('input[type="file"]').on('change', function() {
    $('.recipe-image-label').addClass('valid-label')
})

// Update/add ingredients

function update_checkbox_name() {
    check = $('input[type="checkbox"]')
    check.removeAttr('name')


    var loop_check = 2
    var name_num = 0
    for (i = 0; i < check.length; i++) {
        if (loop_check == i) {
            loop_check += 3
            name_num += 1
        }
        $(check[i]).attr('name', $(check[i]).val() + '-' + name_num)
    }
}

function ingredients_limit() {
    ingredients = $('.ingredient-inputs')
    if (ingredients.length > 20) {
        $(".add-recipe").attr('disabled', true);
    }
    else {
        $(".add-recipe").attr('disabled', false);
    }
}

$('.add-recipe:not([disabled])').on("click", function() {
    $(".example-ingredient").clone().removeClass("example-ingredient").addClass("temp-class").appendTo(".ingredient-form")
    $(".temp-class .ingredient-allergy-info").append('<div class="col m12 s5"><a class="btn-floating right delete-recipe"><i class="material-icons">delete_forever</i></a></div>')
    $(".temp-class input[name='amount']").val("").removeClass("valid");
    $(".temp-class input[name='unit']").val("").removeClass("valid");
    $(".temp-class input[name='ingredient']").val("").removeClass("valid");
    $(".temp-class input[value='gluten-free']").prop('checked', false);
    $(".temp-class input[value='vegan']").prop('checked', false);
    $(".temp-class input[value='vegetarian']").prop('checked', false);
    $(".temp-class").removeClass('temp-class')
    update_checkbox_name()
    ingredients_limit()
})

$(".add-ingredient-container").on("click", '.delete-recipe', function() {
    $(this).closest($(".ingredient-inputs")).remove()
    update_checkbox_name()
    ingredients_limit()
})

$(".add-ingredient-container").on("click", '.vegan', function() {
    if ($(this).is(':checked')) {
        $(this).closest($(".ingredient-allergy-info")).find(".vegetarian").prop("checked", true)
    }
})


$(".add-ingredient-container").on("click", '.vegetarian', function() {
    if (!$(this).is(':checked')) {
        $(this).closest($(".ingredient-allergy-info")).find(".vegan").prop("checked", false)
    }
})
