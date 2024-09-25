# There is no need to create a test environment for these test cases
# because they are not using any file input/output

# Test case 01 - Try to create a text size object
test_that("Text_size creation", {
    # Create a text size object
    obj <- Text_size()
    expect_equal(obj@text_size, 1)
    expect_equal(obj@unit, "pt")
    expect_error(get_size(obj),
    "unable to find an inherited method for function ‘get_size’ for signature ‘object = \"Text_size\"’")
})

# Test case 02 - Try to create a plot text size object
test_that("Plot_text_size creation empty", {
    # Create a plot text size object
    obj <- Plot_text_size()
    expect_equal(obj@plot_width, 1)
    expect_equal(obj@plot_height, 1)
    expect_equal(obj@text_size, 0.04)
    expect_equal(obj@unit, "pt")
    expect_equal(get_size(obj), 0.04)
    expect_equal(get_unit(obj), "pt")
    expect_equal(get_size_format(obj), "0.04pt")
    expect_equal(to_string(obj), "0.04pt")
})

# Test case 03 - Try to create a plot text size with negative values
test_that("Plot_text_size creation negative", {
    # Create a plot text size object
    expect_error(Plot_text_size(
        plot_width = -1,
        plot_height = -1,
        text_size = -1
    ))
})

# Test case 04 - Try to create a vectorized text size object with negative values
test_that("Vectorized_text_size creation negative", {
    # Create a vectorized text size object
    expect_error(Vectorized_text_size(
        num_labels = -1,
        text_size = 20,
        unit = "pt"
    ))
})

# Test case 05 - Try to create a vectorized text size object with good values
test_that("Vectorized_text_size creation good", {
    # Create a vectorized text size object
    obj <- Vectorized_text_size(
        num_labels = 10,
        text_size = 21,
        unit = "pt"
    )
    expect_equal(obj@num_labels, 10)
    expect_equal(obj@text_size, 0.56)
    expect_equal(obj@unit, "pt")
    expect_equal(get_size(obj), 0.56)
})

# Test case 06 - Try to create a vectorized text size with a wrong unit
test_that("Vectorized_text_size creation wrong unit", {
    # Create a vectorized text size object
    expect_error(Text_size(
        text_size = 20,
        unit = "cenmt"
    ), "invalid class “Text_size” object: FALSE")
})