const { app, BrowserWindow, screen, ipcMain } = require('electron');
const { spawn } = require('child_process');

let loginWin = null;
let characterWin = null;
let backendProcess = null;
let loginWindowBounds = null; // 로그인 창의 위치 저장

/**
 * 로그인/시작 창 생성
 */
function createLoginWindow() {
  console.log('🔐 로그인 창 생성');

  loginWin = new BrowserWindow({
    width: 800,
    height: 600,
    center: true,
    resizable: false,
    frame: true,
    backgroundColor: '#ffffff',
    webPreferences: { 
      contextIsolation: false, 
      nodeIntegration: true
      // partition을 설정하지 않으면 앱 종료 시 세션 삭제됨
    }
  });

  // 로그인 페이지 로드 (이미 로그인되어 있으면 자동으로 /start로 이동)
  loginWin.loadURL('http://localhost:8000/login');

  // 개발자 도구는 F12로 수동으로 열 수 있음
  // loginWin.webContents.openDevTools();

  loginWin.on('closed', () => {
    console.log('🔐 로그인 창 닫힘');
    loginWin = null;
  });
  
  // 로그인 창의 위치를 저장 (캐릭터 창을 같은 위치에 띄우기 위해)
  loginWin.on('ready-to-show', () => {
    loginWindowBounds = loginWin.getBounds();
    console.log('📍 로그인 창 위치 저장:', loginWindowBounds);
  });
  
  // 로그인 창을 이동할 때마다 위치 업데이트
  loginWin.on('move', () => {
    loginWindowBounds = loginWin.getBounds();
  });
}

/**
 * 캐릭터 투명 창 생성
 */
function createCharacterWindow() {
  console.log('🎭 투명 전체화면 캐릭터 창 생성');
  
  // 로그인 창이 있던 디스플레이 찾기
  let targetDisplay = screen.getPrimaryDisplay();
  
  if (loginWindowBounds) {
    // 로그인 창의 중앙 위치 계산
    const loginCenterX = loginWindowBounds.x + loginWindowBounds.width / 2;
    const loginCenterY = loginWindowBounds.y + loginWindowBounds.height / 2;
    
    // 로그인 창이 있던 디스플레이 찾기
    const displays = screen.getAllDisplays();
    for (const display of displays) {
      const { x, y, width, height } = display.bounds;
      if (loginCenterX >= x && loginCenterX < x + width &&
          loginCenterY >= y && loginCenterY < y + height) {
        targetDisplay = display;
        console.log('📍 로그인 창이 있던 디스플레이 찾음:', display.id);
        break;
      }
    }
  }
  
  const { x, y, width, height } = targetDisplay.workArea;
  console.log(`📐 캐릭터 창 크기: ${width}x${height}, 위치: (${x}, ${y})`);

  // 전체 화면 투명 창 (클릭-스루 가능)
  characterWin = new BrowserWindow({
    width: width,
    height: height,
    x: x,
    y: y,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: false,
    hasShadow: false,
    skipTaskbar: true,
    backgroundColor: '#00000000',
    webPreferences: { 
      contextIsolation: false, 
      nodeIntegration: true
    }
  });

  // 개발 모드: 캐시 + localStorage 완전 삭제
  characterWin.webContents.session.clearCache().then(() => {
    console.log('🔄 캐시 삭제 완료');
  });
  
  characterWin.webContents.session.clearStorageData({
    storages: ['localstorage']
  }).then(() => {
    console.log('🗑️  localStorage 삭제 완료');
  });
  
  // 메인 페이지 로드 (캐릭터 화면)
  characterWin.loadURL('http://localhost:8000/main');

  console.log('📦 캐릭터 로딩 중...');

  // 🔥 개발자 도구 자동 열기 (detach 모드)
  characterWin.webContents.openDevTools({ mode: 'detach' });
  console.log('🛠️ 개발자 도구 열림 (detach 모드)');

  // 단축키 (F12, Ctrl+Shift+I: 개발자 도구 토글)
  characterWin.webContents.on('before-input-event', (event, input) => {
    // F12로 개발자 도구 (별도 창으로 열기)
    if (input.key === 'F12' || (input.control && input.shift && input.key === 'I')) {
      if (characterWin.webContents.isDevToolsOpened()) {
        characterWin.webContents.closeDevTools();
      } else {
        characterWin.webContents.openDevTools({ mode: 'detach' });
      }
    }
  });

  characterWin.webContents.on('did-finish-load', () => {
    console.log('✅ 캐릭터 로드 완료!');
    
    // 페이지 로드 완료 후 마우스 이벤트 활성화
    // (렌더러에서 동적으로 클릭-스루 영역 제어)
    // 초기에는 마우스 이벤트를 받아서 렌더러에서 처리할 수 있도록 함
    setTimeout(() => {
      if (characterWin && !characterWin.isDestroyed()) {
        characterWin.setIgnoreMouseEvents(false);
        console.log('✅ 마우스 이벤트 활성화');
      }
    }, 1500); // 페이지 초기화 대기 (더 길게)
  });

  // 브라우저 콘솔 메시지를 터미널로 출력 (에러만)
  characterWin.webContents.on('console-message', (event, level, message, line, sourceId) => {
    if (level >= 2) { // 2 = warning, 3 = error
      console.log(`[Browser] ${message}`);
    }
  });

  characterWin.on('closed', () => {
    console.log('🎭 캐릭터 창 닫힘');
    characterWin = null;
  });

  // 개발자 도구 (디버깅용)
  // characterWin.webContents.openDevTools();
}

// 렌더러에서 클릭-스루 영역 정보 받기
ipcMain.on('va:set-ignore-mouse', (_e, ignore) => {
  if (characterWin && !characterWin.isDestroyed()) {
    try {
      characterWin.setIgnoreMouseEvents(ignore, { forward: true });
      // 마우스 이벤트 상태 변경: ignore
    } catch (error) {
      console.error('❌ setIgnoreMouseEvents 오류:', error);
    }
  }
});

// 보고서 패널 열릴 때 alwaysOnTop 제어
ipcMain.on('va:report-panel-toggle', (_e, isOpen) => {
  if (characterWin && !characterWin.isDestroyed()) {
    try {
      if (isOpen) {
        // 보고서 패널 열릴 때: alwaysOnTop 끄기
        characterWin.setAlwaysOnTop(false);
        console.log('📝 보고서 패널 열림 → alwaysOnTop: false');
      } else {
        // 보고서 패널 닫힐 때: alwaysOnTop 켜기
        characterWin.setAlwaysOnTop(true);
        console.log('📝 보고서 패널 닫힘 → alwaysOnTop: true');
      }
    } catch (error) {
      console.error('❌ setAlwaysOnTop 오류:', error);
    }
  }
});

// 시작하기 버튼 클릭 시 캐릭터 창 생성
ipcMain.on('va:start-character', () => {
  console.log('✨ 캐릭터 시작!');
  
  // 캐릭터 창이 없으면 생성
  if (!characterWin) {
    createCharacterWindow();
  }
  
  // 로그인 창 닫기
  if (loginWin && !loginWin.isDestroyed()) {
    loginWin.close();
  }
});

// 로그아웃 시 로그인 창으로 돌아가기
ipcMain.on('va:logout', () => {
  console.log('👋 로그아웃');
  
  // 캐릭터 창 닫기
  if (characterWin && !characterWin.isDestroyed()) {
    characterWin.close();
  }
  
  // 로그인 창 생성
  if (!loginWin) {
    createLoginWindow();
  }
});

// 종료 요청 (다이얼로그에서 확인 후)
ipcMain.on('va:request-quit', () => {
  console.log('✅ 사용자가 종료를 확인함');
  app.quit();
});

// 백엔드 서버가 준비될 때까지 대기하는 함수
async function waitForBackend(maxRetries = 60) {
  const http = require('http');
  
  for (let i = 0; i < maxRetries; i++) {
    try {
      await new Promise((resolve, reject) => {
        const req = http.get('http://localhost:8000/health', { timeout: 2000 }, (res) => {
          if (res.statusCode === 200) {
            resolve();
          } else {
            reject(new Error(`Status: ${res.statusCode}`));
          }
        });
        req.on('error', reject);
        req.on('timeout', () => {
          req.destroy();
          reject(new Error('Request timeout'));
        });
      });
      
      console.log('✅ 백엔드 서버 준비 완료!');
      return true;
    } catch (err) {
      if (i % 5 === 0 || i === maxRetries - 1) {  // 5초마다 또는 마지막에만 로그 출력
        console.log(`⏳ 백엔드 대기 중... (${i + 1}/${maxRetries})`);
      }
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  }
  
  console.error('❌ 백엔드 서버 시작 타임아웃');
  return false;
}

app.whenReady().then(async () => {
  console.log('🚀 일렉트론 앱 시작!');
  console.log('📝 세션 기반 - 앱 종료 시 로그인 정보 삭제됨');
  console.log('⌨️  단축키: ESC = 종료, F12 = 개발자 도구');
  
  // 백엔드 서버 시작
  console.log('🔧 백엔드 서버 시작 중...');
  
  // 작업 디렉토리를 프로젝트 루트로 설정
  const path = require('path');
  const projectRoot = __dirname;
  
  backendProcess = spawn('python', ['assistant.py'], {
    cwd: projectRoot,  // 프로젝트 루트에서 실행
    stdio: ['ignore', 'pipe', 'pipe'],  // stdout, stderr를 파이프로 받아서 처리
    shell: true,
    env: {
      ...process.env,
      PYTHONIOENCODING: 'utf-8',
      PYTHONUTF8: '1'
    }
  });
  
  // 백엔드 출력을 콘솔로 전달
  backendProcess.stdout.on('data', (data) => {
    console.log(`[Backend] ${data.toString().trim()}`);
  });
  
  backendProcess.stderr.on('data', (data) => {
    console.error(`[Backend Error] ${data.toString().trim()}`);
  });
  
  backendProcess.on('error', (err) => {
    console.error('❌ 백엔드 서버 시작 실패:', err);
  });
  
  backendProcess.on('exit', (code, signal) => {
    if (code !== null) {
      console.log(`📴 백엔드 서버 종료됨 (코드: ${code})`);
    } else {
      console.log(`📴 백엔드 서버 종료됨 (시그널: ${signal})`);
    }
  });
  
  // 백엔드가 준비될 때까지 대기 (최대 60초)
  const ready = await waitForBackend(60);
  
  if (ready) {
    // 백엔드 준비 완료 후 로그인 창 띄움
    createLoginWindow();
  } else {
    console.error('❌ 백엔드를 시작할 수 없습니다.');
    if (backendProcess && !backendProcess.killed) {
      backendProcess.kill('SIGTERM');
    }
    app.quit();
  }
});

app.on('window-all-closed', () => { 
  console.log('👋 앱 종료 중...');
  
  // 백엔드 프로세스 종료
  if (backendProcess && !backendProcess.killed) {
    console.log('🛑 백엔드 서버 종료 중...');
    backendProcess.kill('SIGTERM');
  }
  
  // 세션 삭제 (로그인 정보 초기화)
  const { session } = require('electron');
  session.defaultSession.clearStorageData({
    storages: ['cookies', 'localstorage', 'sessionstorage']
  }).then(() => {
    console.log('🗑️  세션 삭제 완료');
    app.quit();
  });
});

app.on('activate', () => { 
  if (BrowserWindow.getAllWindows().length === 0) {
    createLoginWindow();
  }
});

// 앱 종료 전 정리
app.on('before-quit', () => {
  console.log('🧹 앱 종료 전 정리 중...');
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill('SIGTERM');
  }
});
