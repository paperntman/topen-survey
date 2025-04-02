let start_time, button_time;

start_time = Date.now();

$('#showQ').on('click', function() {
    button_time = Date.now();
    $('.hidden').removeClass('hidden');
});

$('#reload').on('click', function() {
    location.reload(true);
});

$('#submit').on('click', function(event) {
    event.preventDefault(); // 기본 폼 제출 방지

    const urlParams = new URLSearchParams(window.location.search);
    const pageParam = urlParams.get('page') || '00000000';
    // 폼 데이터 수집
    let formData = $('#form').serializeArray();
    
    // 추가 데이터
    formData.push({ name: 'button_time', value: button_time-start_time });
    formData.push({ name: 'submit_time', value: Date.now()-button_time });
    formData.push({ name: 'id', value: document.title})
    formData.push({ name: 'page', value: pageParam });

    // POST 요청 보내기
    $.ajax({
        url: '/post',
        type: 'POST',
        data: formData,
        success: function(data) {
            console.log('Success:', data);
            window.location.href = data.redirect_url;
            // location.reload(true)
            // 성공적으로 데이터가 전송된 후의 처리
        },
        error: function(xhr, status, error) {
            console.error('Error:', error);
            // location.reload(true)
            // 오류 처리
        }
    });
    
});
