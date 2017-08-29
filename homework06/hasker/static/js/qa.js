!function ($) {
    var Vote = function (element) {
        this.$element = $(element);
    }

    Vote.prototype.update = function(url, value) {
        var $i = this.$element.find('i');
        var $span = $i.find('span');
        $.ajax({
            url: url,
            type: "post",
            data: {
                "value": value
            },
            dataType: "json",
            success: function(data) {
                $span.text(data.votes);
            }
        })
    }

    $.fn.vote = function(url, value) {
        return this.each(function () {
            var $this = $(this),
                data = $this.data('jpl.vote');

            if (!data) $this.data('jpl.vote', (data = new Vote(this)));
            if (typeof value == 'number') data.update(url, value);
        })
    };

    $(document).on('click', 'a.vote', function(e) {
        e.preventDefault();
        var $this = $(this);
        var target = $($this.data('target'));
        var href = $this.attr('href');
        var value = $this.data('value');
        target.vote(href, value);
    });

    $(document).on('click', 'a.mark', function(e) {
        e.preventDefault();
        var $this = $(this);
        var url = $this.attr('href');
        $.ajax({
            url: url,
            type: "post",
            dataType: "json",
            success: function(data) {
                if (data.mark) {
                    if ($this.hasClass("green")) {
                        $this.removeClass('green').addClass('grey');
                    } else {
                        $this.removeClass('grey').addClass('green');
                    }
                }
            }
        })
    });
}(window.jQuery);
