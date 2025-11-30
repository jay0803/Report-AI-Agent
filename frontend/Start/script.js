/**
 * 쿠키에서 값 가져오기
 */
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
        return decodeURIComponent(parts.pop().split(';').shift());
    }
    return null;
}

/**
 * 로그인 여부 확인 (쿠키에서)
 * 
 * 참고: access_token은 HttpOnly 쿠키라서 JavaScript에서 읽을 수 없음
 * 대신 logged_in 플래그 쿠키를 확인
 */
function isLoggedIn() {
    const loggedIn = getCookie('logged_in');
    return loggedIn === 'true';
}

/**
 * 사용자 정보 가져오기 (쿠키에서)
 */
function getUserInfo() {
    const userEncoded = getCookie('user');
    if (userEncoded) {
        try {
            // URL 디코딩 후 JSON 파싱
            const userJson = decodeURIComponent(userEncoded);
            return JSON.parse(userJson);
        } catch (e) {
            console.error('사용자 정보 파싱 실패:', e);
            return null;
        }
    }
    return null;
}

/**
 * 쿠키 삭제
 */
function deleteCookie(name) {
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
}

/**
 * 로그아웃
 */
function logout() {
    if (confirm('정말 로그아웃하시겠습니까?')) {
        console.log('🚪 로그아웃 - 쿠키 삭제');
        
        // 쿠키에서 토큰 및 사용자 정보 삭제
        deleteCookie('access_token');
        deleteCookie('refresh_token');
        deleteCookie('user');
        deleteCookie('logged_in');
        
        // 로그인 페이지로 이동 (같은 창에서)
        console.log('🔐 로그인 페이지로 이동');
        window.location.href = '/login?logout=true';
    }
}

/**
 * 시작하기 버튼 클릭
 */
function startAssistant() {
    console.log('시작하기 버튼 클릭!');
    
    // Electron인지 확인
    if (typeof window.require !== 'undefined') {
        try {
            // Electron에서는 IPC로 캐릭터 창 열기
            const { ipcRenderer } = window.require('electron');
            console.log('IPC 메시지 전송: va:start-character');
            ipcRenderer.send('va:start-character');
        } catch (err) {
            console.error('IPC 전송 실패:', err);
            alert('캐릭터 창을 열 수 없습니다.');
        }
    } else {
        // 브라우저에서는 메인 페이지로 이동
        console.log('브라우저 모드 - /main으로 이동');
        window.location.href = '/main';
    }
}

/**
 * 페이지 로드 시 실행
 */
window.addEventListener('DOMContentLoaded', () => {
    console.log('📄 Start 페이지 로드');
    console.log('🍪 전체 쿠키:', document.cookie);
    
    // 각 쿠키 개별 확인
    const loggedIn = getCookie('logged_in');
    const user = getCookie('user');
    
    console.log('✅ logged_in:', loggedIn);
    console.log('👤 user:', user ? user : '❌ 없음');
    console.log('ℹ️  참고: access_token, refresh_token은 HttpOnly 쿠키라서 JavaScript에서 읽을 수 없습니다.');
    
    // 로그인 확인 (쿠키에서)
    if (!isLoggedIn()) {
        console.error('❌ 로그인 안 됨 - /login으로 이동');
        console.error('   원인: logged_in 쿠키가 없거나 false입니다');
        window.location.href = '/login';
        return;
    }
    
    console.log('✅ 로그인 확인됨 (쿠키)');

    // 사용자 정보 표시
    const userInfo = getUserInfo();
    if (userInfo) {
        const userNameEl = document.getElementById('userName');
        if (userNameEl) {
            userNameEl.textContent = userInfo.name || userInfo.email || '사용자님';
        }
        console.log('👤 사용자 정보:', userInfo);
    }

    // 시작하기 버튼 이벤트
    const startBtn = document.getElementById('startBtn');
    if (startBtn) {
        startBtn.addEventListener('click', startAssistant);
    }
});

