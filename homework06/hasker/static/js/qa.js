function mark(answerId) {
    $.ajax({
        url: "/answer/" + answerId + "/mark",
        type: "post",
        dataType: "json",
        success: function(data) {
            if (data.mark) {
                var el = $("#answer" + answerId);
                if (el.attr("class").toString() == "ui right floated grey label") {
                    el.removeClass("ui right floated grey label");
                    el.addClass("ui right floated green label");
                } else {
                    el.removeClass("ui right floated green label");
                    el.addClass("ui right floated grey label");
                }
            }
        }
    })
}

function questionVote(qId, value) {
    $.ajax({
        url: "/question/" + qId + "/vote",
        type: "post",
        data: {
            "value": value
        },
        dataType: "json",
        success: function(data) {
            var question_vote = $("#question_vote");
            question_vote.text(data.votes);
        },
   })
}

function questionVoteUp(qId) {
    questionVote(qId, 1);
}

function questionVoteDown(qId) {
    questionVote(qId, -1);
}

function answerVote(id, value) {
    $.ajax({
        url: "/answer/" + id + "/vote",
        type: "post",
        data: {
            "value": value
        },
        dataType: "json",
        success: function(data) {
            var answer_vote = $("#answer_vote" + id);
            answer_vote.text(data.votes);
        },
   })
}

function answerVoteDown(aId) {
    answerVote(aId, -1);
}

function answerVoteUp(aId) {
    answerVote(aId, 1);
}
