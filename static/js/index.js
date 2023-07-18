// GelSight image viewer call back functions
// Created by Alan Zhao (alanzhao@csail.mit.edu)

// Button call back functions
$('a#btn-ref').on('click', function(e) {
        e.preventDefault();
        console.log("Refresh button pressed.");
        $.getJSON('/btn_refresh',
            function(data) {
        });
        location.reload();
        return false;
});

// Mode button text update calls
function update_mode_button_text(){
    $.get("/update_btn_mode", function(data){
        $("#btn-value").html(data);
    });
}

$('a#btn-mode').on('click', function(e) {
        e.preventDefault();
        console.log("Mode switching button pressed.");
        $.getJSON('/btn_mode',
            function(data) {
        });

        update_mode_button_text();
        return false;
});

// Text update calls
function update_fps(){
    $.get("/update_fps", function(data){
        $("#fps").html(data)
    });
}

update_fps()
update_mode_button_text()
var intervalId = setInterval(function() {
    update_fps()
}, 500);