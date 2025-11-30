/**
 * Activity Monitor Module - Public API
 * 
 * 사용 예시:
 * ```javascript
 * import { setupActivityMonitor } from './renderer/activity-monitor/index.js';
 * 
 * const cleanup = setupActivityMonitor({
 *   mode: 'dev', // 또는 'prod'
 *   onIdle: () => {
 *     console.log('사용자가 쉬고 있어요!');
 *     // 캐릭터 모션: model.motion('Idle');
 *   },
 *   onLongActive: () => {
 *     console.log('너무 오래 일하고 있어요!');
 *     // 캐릭터 모션: model.motion('Tap@Body');
 *   }
 * });
 * 
 * // 정리가 필요할 때
 * cleanup();
 * ```
 */

export { setupActivityMonitor, getActivityStatus } from './activityMonitor.js';


