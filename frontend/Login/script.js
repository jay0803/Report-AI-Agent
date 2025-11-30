// API Base URL
const API_BASE_URL = 'http://localhost:8000/api/v1';

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
 * 쿠키 삭제
 */
function deleteCookie(name) {
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
}

/**
 * Google 로그인
 */
async function loginWithGoogle() {
    try {
        console.log('🔵 Google 로그인 시작');
        showLoading('google-btn');
        
        // 백엔드에서 Google OAuth URL 가져오기
        const response = await fetch(`${API_BASE_URL}/auth/google/login`);
        const data = await response.json();
        
        if (data.authorization_url) {
            console.log('🔵 Google OAuth URL로 이동:', data.authorization_url);
            // 현재 창에서 리다이렉트 (Electron & 브라우저 공통)
            window.location.href = data.authorization_url;
        } else {
            throw new Error('Google 로그인 URL을 가져올 수 없습니다.');
        }
    } catch (error) {
        console.error('Google 로그인 에러:', error);
        alert('Google 로그인 중 오류가 발생했습니다. 다시 시도해주세요.');
        hideLoading('google-btn');
    }
}

/**
 * Kakao 로그인
 */
async function loginWithKakao() {
    try {
        console.log('🟡 Kakao 로그인 시작');
        showLoading('kakao-btn');
        
        const response = await fetch(`${API_BASE_URL}/auth/kakao/login`);
        const data = await response.json();
        
        if (data.authorization_url) {
            console.log('🟡 Kakao OAuth URL로 이동:', data.authorization_url);
            // 현재 창에서 리다이렉트
            window.location.href = data.authorization_url;
        } else {
            throw new Error('Kakao 로그인 URL을 가져올 수 없습니다.');
        }
    } catch (error) {
        console.error('Kakao 로그인 에러:', error);
        alert('Kakao 로그인 중 오류가 발생했습니다. 다시 시도해주세요.');
        hideLoading('kakao-btn');
    }
}

/**
 * Naver 로그인
 */
async function loginWithNaver() {
    try {
        console.log('🟢 Naver 로그인 시작');
        showLoading('naver-btn');
        
        const response = await fetch(`${API_BASE_URL}/auth/naver/login`);
        const data = await response.json();
        
        if (data.authorization_url) {
            console.log('🟢 Naver OAuth URL로 이동:', data.authorization_url);
            // 현재 창에서 리다이렉트
            window.location.href = data.authorization_url;
        } else {
            throw new Error('Naver 로그인 URL을 가져올 수 없습니다.');
        }
    } catch (error) {
        console.error('Naver 로그인 에러:', error);
        alert('Naver 로그인 중 오류가 발생했습니다. 다시 시도해주세요.');
        hideLoading('naver-btn');
    }
}

/**
 * 게스트로 계속하기
 */
function continueAsGuest() {
    // 게스트 모드로 메인 페이지로 이동
    alert('게스트 모드는 아직 구현되지 않았습니다.');
    // window.location.href = '/index.html?mode=guest';
}

/**
 * OAuth 콜백 처리
 * 백엔드가 직접 /start로 리다이렉트하므로 여기서는 에러만 처리
 */
async function handleOAuthCallback() {
    const urlParams = new URLSearchParams(window.location.search);
    const error = urlParams.get('error');
    
    // 에러가 있으면 처리
    if (error) {
        console.error('OAuth 에러:', error);
        alert('로그인이 취소되었거나 오류가 발생했습니다.');
        // URL에서 쿼리 파라미터 제거
        window.history.replaceState({}, document.title, window.location.pathname);
        return;
    }
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
 * 로그아웃 (쿠키 삭제)
 */
function logout(redirect = true) {
    deleteCookie('access_token');
    deleteCookie('refresh_token');
    deleteCookie('user');
    deleteCookie('logged_in');
    
    if (redirect) {
        window.location.href = '/';
    }
}

/**
 * 로딩 표시
 */
function showLoading(buttonClass) {
    const button = document.querySelector(`.${buttonClass}`);
    if (button) {
        button.classList.add('loading');
        button.disabled = true;
    }
}

/**
 * 로딩 숨김
 */
function hideLoading(buttonClass) {
    const button = document.querySelector(`.${buttonClass}`);
    if (button) {
        button.classList.remove('loading');
        button.disabled = false;
    }
}

/**
 * 페이지 로드 시 실행
 */
window.addEventListener('DOMContentLoaded', () => {
    console.log('📄 Login 페이지 로드');
    console.log('🍪 현재 쿠키:', document.cookie);
    
    // OAuth 에러 처리
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('error')) {
        handleOAuthCallback();
    }
    
    // 이미 로그인 되어있으면 시작 페이지로 리다이렉트
    // (단, 명시적으로 로그인 페이지를 요청한 경우는 제외)
    const loggedIn = getCookie('logged_in');
    console.log('✅ logged_in 쿠키:', loggedIn);
    console.log('ℹ️  참고: access_token은 HttpOnly 쿠키라서 JavaScript에서 읽을 수 없습니다.');
    
    if (isLoggedIn() && !urlParams.has('logout')) {
        console.log('✅ 이미 로그인됨 - /start로 이동');
        window.location.href = '/start';
        return;
    }
    
    console.log('🔐 로그인 필요');
});
