"""
浏览器控制模块，负责浏览器实例的创建、页面访问和元素操作
优化版本：减少频繁重启，添加智能错误恢复机制
"""
import asyncio
import time
from playwright.async_api import async_playwright
from src.core.config.config import (
    BROWSER_DATA_DIR, DEFAULT_TIMEOUT, DEFAULT_WAIT_TIME, 
    VIEWPORT_WIDTH, VIEWPORT_HEIGHT
)
from src.core.logging.logger import logger
from datetime import datetime


class BrowserManager:
    """浏览器管理类，处理浏览器实例的创建、页面访问和元素操作
    
    优化特性：
    - 分级错误恢复策略
    - 智能重试机制
    - 减少不必要的重启
    - 状态缓存机制
    """
    
    def __init__(self):
        """初始化浏览器管理器"""
        self.playwright_instance = None
        self.browser_context = None
        self.main_page = None
        self.is_logged_in = False
        self.last_health_check = 0
        self.restart_count = 0
        self.max_restarts_per_hour = 3  # 每小时最多重启3次
        self.restart_timestamps = []
        self._browser_healthy = True  # 浏览器健康状态标志
        
        # 引入登录状态管理器（延迟初始化）
        self._login_manager = None
        
        logger.info("BrowserManager 初始化完成")
    
    @property
    def login_manager(self):
        """获取登录状态管理器（懒加载）"""
        if self._login_manager is None:
            from src.infrastructure.browser.login_manager import LoginStateManager
            self._login_manager = LoginStateManager(self)
        return self._login_manager
    
    async def ensure_browser(self, force_check=False):
        """确保浏览器正常运行，优化版本：避免频繁重启
        
        Args:
            force_check (bool): 是否强制检查浏览器状态
            
        Returns:
            bool: 浏览器是否可用
        """
        try:
            current_time = time.time()
            
            # 清理过期的重启记录
            self.restart_timestamps = [t for t in self.restart_timestamps if current_time - t < 3600]
            
            # 检查重启频率限制
            if len(self.restart_timestamps) >= self.max_restarts_per_hour:
                logger.warning(f"浏览器重启过于频繁，当前小时内已重启 {len(self.restart_timestamps)} 次")
                return False
            
            # 快速路径：如果浏览器正常且最近检查过，直接返回
            if not force_check and self.browser_context and self.main_page:
                # 减少健康检查频率：从30秒增加到300秒（5分钟）
                if current_time - self.last_health_check < 300:
                    return True
            
            # 如果浏览器未启动，先启动
            if not self.browser_context or not self.main_page:
                logger.info("浏览器未启动，正在启动...")
                await self._start_browser()
                
                # 启动后自动尝试恢复登录状态
                try:
                    login_restored = await self.login_manager.auto_restore_login()
                    if login_restored:
                        logger.info("浏览器启动后成功恢复登录状态")
                    else:
                        logger.info("浏览器启动完成，但未恢复登录状态")
                except Exception as e:
                    logger.warning(f"恢复登录状态时出错: {str(e)}")
                
                return True
            
            # 检查浏览器健康状态
            if await self._needs_browser_restart():
                logger.warning("检测到浏览器异常，准备重启")
                if self._can_restart():
                    await self._safe_restart()
                    return True
                else:
                    logger.error("无法重启浏览器（超出限制）")
                    return False
            
            # 更新健康检查时间
            self.last_health_check = current_time
            return True
            
        except Exception as e:
            logger.error(f"确保浏览器运行时出错: {str(e)}")
            
            # 异常时尝试轻量级恢复
            if self._can_restart():
                try:
                    await self._light_recovery()
                    return True
                except Exception as recovery_error:
                    logger.error(f"轻量级恢复失败: {str(recovery_error)}")
            
            return False
    
    async def _needs_browser_restart(self):
        """检查是否需要重启浏览器（优化版）"""
        # 基础检查：实例是否存在
        if self.browser_context is None or self.playwright_instance is None:
            return True
            
        # 优化：分级状态检查，从轻到重
        try:
            # 级别1：快速检查基本状态
            if not hasattr(self.browser_context, 'pages'):
                return True
            
            # 级别2：检查页面是否有效
            if self.main_page is None:
                # 尝试获取现有页面而不是重启
                pages = self.browser_context.pages
                if pages:
                    self.main_page = pages[0]
                    logger.info("恢复了现有页面实例")
                    return False
                else:
                    return True
            
            # 级别3：检查页面是否关闭（最耗时的检查）
            if hasattr(self.main_page, 'is_closed'):
                is_closed = await self.main_page.is_closed()
                if is_closed:
                    return True
                    
        except Exception as e:
            logger.warning(f"浏览器状态检查异常: {str(e)}")
            # 某些异常可能是临时的，不一定需要重启
            if "closed" in str(e).lower() or "disconnected" in str(e).lower():
                return True
            # 其他异常先尝试轻量级恢复
            return False
            
        return False
    
    def _can_restart(self):
        """检查是否可以重启浏览器（基于频率限制）
        
        Returns:
            bool: 是否可以重启
        """
        current_time = time.time()
        
        # 清理过期的重启记录（1小时前的）
        self.restart_timestamps = [t for t in self.restart_timestamps if current_time - t < 3600]
        
        # 检查是否超过小时限制
        if len(self.restart_timestamps) >= self.max_restarts_per_hour:
            logger.warning(f"浏览器重启过于频繁，当前小时内已重启 {len(self.restart_timestamps)} 次")
            return False
        
        logger.info(f"允许重启，当前小时内重启次数: {len(self.restart_timestamps)}/{self.max_restarts_per_hour}")
        return True
    
    async def _light_recovery(self):
        """轻量级恢复：尝试修复而不是重启整个浏览器"""
        try:
            logger.info("尝试轻量级恢复")
            
            # 恢复方案1：创建新页面
            if self.browser_context and hasattr(self.browser_context, 'new_page'):
                try:
                    self.main_page = await self.browser_context.new_page()
                    self.main_page.set_default_timeout(DEFAULT_TIMEOUT)
                    # 为新页面注入完整的反检测配置
                    await self._inject_stealth_scripts()
                    await self._hide_automation_bar()
                    logger.info("成功创建新页面并应用完整反检测配置")
                    return True
                except Exception:
                    pass
            
            # 恢复方案2：使用现有页面
            if self.browser_context and hasattr(self.browser_context, 'pages'):
                pages = self.browser_context.pages
                if pages:
                    self.main_page = pages[0]
                    # 为现有页面重新注入反检测脚本（可能已失效）
                    try:
                        await self._inject_stealth_scripts()
                        await self._hide_automation_bar()
                        logger.info("成功恢复现有页面并重新应用反检测配置")
                    except Exception as e:
                        logger.warning(f"为现有页面重新应用反检测配置失败: {str(e)}")
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"轻量级恢复失败: {str(e)}")
            return False
    
    async def _safe_restart(self):
        """安全重启浏览器，确保资源正确释放和恢复"""
        try:
            current_time = time.time()
            
            logger.info("开始安全重启浏览器...")
            
            # 先保存当前登录状态（如果已登录）
            if self.is_logged_in:
                try:
                    await self.login_manager.save_login_state({
                        "restart_reason": "browser_restart",
                        "restart_time": datetime.now().isoformat()
                    })
                except Exception as e:
                    logger.warning(f"保存登录状态失败: {str(e)}")
            
            # 关闭现有浏览器
            if self.browser_context:
                try:
                    await self.browser_context.close()
                except Exception as e:
                    logger.warning(f"关闭浏览器上下文时出错: {str(e)}")
            
            if self.playwright_instance:
                try:
                    await self.playwright_instance.stop()
                except Exception as e:
                    logger.warning(f"停止Playwright实例时出错: {str(e)}")
            
            # 重置状态
            self.browser_context = None
            self.main_page = None
            self.playwright_instance = None
            
            # 记录重启时间
            self.restart_timestamps.append(current_time)
            
            # 启动新的浏览器实例
            await self._start_browser()
            
            # 尝试恢复登录状态
            try:
                login_restored = await self.login_manager.auto_restore_login()
                if login_restored:
                    logger.info("重启后成功恢复登录状态")
                else:
                    logger.info("重启完成，但未恢复登录状态")
            except Exception as e:
                logger.warning(f"重启后恢复登录状态失败: {str(e)}")
            
            logger.info("浏览器安全重启完成")
            
        except Exception as e:
            logger.error(f"安全重启浏览器失败: {str(e)}")
            raise e
    
    async def _start_browser(self):
        """启动浏览器并创建上下文"""
        # 在启动前先主动处理可能的冲突
        await self._handle_singleton_conflict()
        
        # 记录启动次数
        restart_count = 0
        max_restart_attempts = 3
        
        while restart_count < max_restart_attempts:
            try:
                restart_count += 1
                logger.info(f"[BrowserManager] 开始启动浏览器 (第{restart_count}次)")
                
                # 启动浏览器
                self.playwright_instance = await async_playwright().start()
                
                # 极简反检测配置：完全移除可能触发警告的参数，改用纯JS反检测
                browser_args = [
                    # 基础参数（不会触发任何警告）
                    '--exclude-switches=enable-automation',  # 排除自动化开关
                    '--disable-extensions',  # 禁用扩展
                    '--disable-plugins',  # 禁用插件
                    '--disable-default-apps',  # 禁用默认应用
                    '--disable-popup-blocking',  # 禁用弹窗阻止
                    '--disable-translate',  # 禁用翻译
                    '--disable-features=Translate,OptimizationHints',  # 禁用翻译等功能
                    '--no-first-run',  # 跳过首次运行
                    '--no-default-browser-check',  # 跳过默认浏览器检查
                    '--disable-component-update',  # 禁用组件更新
                    '--disable-background-timer-throttling',  # 禁用后台定时器限制
                    '--disable-renderer-backgrounding',  # 禁用渲染器后台
                    '--disable-backgrounding-occluded-windows',  # 禁用后台窗口
                    '--disable-hang-monitor',  # 禁用挂起监视器
                    '--disable-prompt-on-repost',  # 禁用重新发布时的提示
                    '--disable-sync',  # 禁用同步
                    '--disable-background-networking',  # 禁用后台网络
                    '--disable-domain-reliability',  # 禁用域名可靠性
                    '--disable-client-side-phishing-detection',  # 禁用客户端钓鱼检测
                    '--disable-background-mode',  # 禁用后台模式
                    '--metrics-recording-only',  # 仅记录指标
                    '--disable-infobars',  # 禁用信息栏
                    '--disable-save-password-bubble',  # 禁用保存密码气泡
                ]
                
                # 真实的User Agent（模拟最新Chrome浏览器）
                realistic_user_agent = (
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                )
                
                # 使用持久化上下文来保存用户状态
                self.browser_context = await self.playwright_instance.chromium.launch_persistent_context(
                    user_data_dir=BROWSER_DATA_DIR,
                    headless=False,  # 非隐藏模式，方便用户登录
                    viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
                    timeout=DEFAULT_TIMEOUT,
                    args=browser_args,  # 添加强化的反检测参数
                    user_agent=realistic_user_agent,  # 设置真实User Agent
                    # 额外的反检测配置
                    locale='zh-CN',  # 设置中文本地化
                    timezone_id='Asia/Shanghai',  # 设置中国时区
                    permissions=['geolocation', 'notifications'],  # 授予常见权限
                    # 屏幕和设备信息
                    screen={'width': 1920, 'height': 1080},
                    device_scale_factor=1,
                    # 禁用自动化标志
                    ignore_default_args=[
                        '--enable-automation',
                        '--no-sandbox',         # 关键：忽略no-sandbox参数，避免安全警告
                    ],
                    # 额外参数
                    extra_http_headers={
                        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                        'Cache-Control': 'no-cache',
                        'Pragma': 'no-cache',
                        'Sec-Fetch-Site': 'none',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-User': '?1',
                        'Upgrade-Insecure-Requests': '1',
                    }
                )
                
                # 创建一个新页面
                if self.browser_context.pages:
                    self.main_page = self.browser_context.pages[0]
                else:
                    self.main_page = await self.browser_context.new_page()
                
                # 设置页面级别的超时时间
                self.main_page.set_default_timeout(DEFAULT_TIMEOUT)
                
                # 高级反检测：注入JavaScript脚本来伪装浏览器环境
                await self._inject_stealth_scripts()
                
                # 额外：隐藏自动化信息栏的CSS注入
                await self._hide_automation_bar()
                
                logger.info("[BrowserManager] 浏览器启动成功")
                self._browser_healthy = True
                
                # 添加浏览器实例创建的时间戳记录（用于限制重启频率）
                current_time = time.time()
                self.restart_timestamps.append(current_time)
                
                # 成功启动，返回
                return
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"[BrowserManager] 浏览器启动失败: {error_msg}")
                
                # 特殊处理：浏览器实例冲突
                if "ProcessSingleton" in error_msg or "SingletonLock" in error_msg:
                    logger.warning("检测到浏览器实例冲突，尝试清理并重试")
                    await self._handle_singleton_conflict()
                    # 继续下一次循环重试
                    continue
                
                # 关闭任何可能已创建的实例
                try:
                    if self.browser_context:
                        await self.browser_context.close()
                    if self.playwright_instance:
                        await self.playwright_instance.stop()
                except Exception:
                    pass
                
                # 重置状态
                self.browser_context = None
                self.main_page = None
                self.playwright_instance = None
                
                # 最后一次尝试失败时，抛出异常
                if restart_count >= max_restart_attempts:
                    logger.error(f"启动浏览器失败 (尝试 {restart_count}/{max_restart_attempts}): {error_msg}")
                    raise e
                
                # 等待一段时间后重试
                await asyncio.sleep(1)
        
        # 所有重试都失败
        raise Exception("启动浏览器最终失败，已达到最大重试次数")
    
    async def _inject_stealth_scripts(self):
        """注入超强反检测脚本，完全依靠JavaScript隐藏自动化特征"""
        stealth_script = """
        () => {
            // === 第一层：基础自动化标识清除 ===
            
            // 完全移除和重定义 webdriver 属性 - 强力版本
            try {
                delete navigator.webdriver;
                delete Navigator.prototype.webdriver;
            } catch(e) {}
            
            // 使用多种方法确保webdriver属性被隐藏
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
                set: () => {},
                configurable: true,
                enumerable: false
            });
            
            // 重写整个navigator.webdriver属性描述符
            const webdriverDescriptor = {
                get: () => false,
                set: () => {},
                configurable: false,
                enumerable: false
            };
            
            try {
                Object.defineProperty(navigator, 'webdriver', webdriverDescriptor);
                Object.defineProperty(Navigator.prototype, 'webdriver', webdriverDescriptor);
            } catch(e) {
                // 如果上面的方法失败，使用替代方法
                navigator.__defineGetter__('webdriver', () => false);
                Navigator.prototype.__defineGetter__('webdriver', () => false);
            }
            
            // 最终确保：直接重写值
            navigator.webdriver = false;
            
            // 清除可能的自动化检测属性
            delete navigator.__webdriver_script_fn;
            delete navigator.__driver_evaluate;
            delete navigator.__webdriver_evaluate;
            delete navigator.__selenium_evaluate;
            delete navigator.__fxdriver_evaluate;
            delete navigator.__driver_unwrapped;
            delete navigator.__webdriver_unwrapped;
            delete navigator.__selenium_unwrapped;
            delete navigator.__fxdriver_unwrapped;
            
            // === 第二层：深度环境伪装 ===
            
            // 重写 plugins 对象，模拟真实浏览器
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    const plugins = [
                        {
                            0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format", enabledPlugin: "[object Plugin]"},
                            description: "Portable Document Format",
                            filename: "internal-pdf-viewer",
                            length: 1,
                            name: "Chrome PDF Plugin"
                        },
                        {
                            0: {type: "application/pdf", suffixes: "pdf", description: "", enabledPlugin: "[object Plugin]"},
                            description: "",
                            filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                            length: 1,
                            name: "Chrome PDF Viewer"
                        },
                        {
                            0: {type: "application/x-nacl", suffixes: "", description: "Native Client Executable", enabledPlugin: "[object Plugin]"},
                            1: {type: "application/x-pnacl", suffixes: "", description: "Portable Native Client Executable", enabledPlugin: "[object Plugin]"},
                            description: "",
                            filename: "internal-nacl-plugin",
                            length: 2,
                            name: "Native Client"
                        },
                        {
                            0: {type: "application/x-ppapi-widevine-cdm", suffixes: "", description: "Widevine Content Decryption Module", enabledPlugin: "[object Plugin]"},
                            description: "Enables Widevine licenses for playback of HTML audio/video content.",
                            filename: "widevinecdmadapter.plugin",
                            length: 1,
                            name: "Widevine Content Decryption Module"
                        },
                        {
                            0: {type: "application/x-shockwave-flash", suffixes: "swf", description: "Shockwave Flash", enabledPlugin: "[object Plugin]"},
                            description: "Shockwave Flash 32.0 r0",
                            filename: "pepflashplayer.plugin",
                            length: 1,
                            name: "Shockwave Flash"
                        }
                    ];
                    Object.setPrototypeOf(plugins, PluginArray.prototype);
                    return plugins;
                },
                configurable: false,
                enumerable: true
            });
            
            // 伪装语言配置
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en-US', 'en'],
                configurable: false,
                enumerable: true
            });
            
            // 伪装平台信息
            Object.defineProperty(navigator, 'platform', {
                get: () => 'MacIntel',
                configurable: false,
                enumerable: true
            });
            
            // 伪装硬件信息
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8,
                configurable: false,
                enumerable: true
            });
            
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8,
                configurable: false,
                enumerable: true
            });
            
            Object.defineProperty(navigator, 'maxTouchPoints', {
                get: () => 0,
                configurable: false,
                enumerable: true
            });
            
            // === 第三层：Chrome对象完整伪装 ===
            
            if (!window.chrome) {
                Object.defineProperty(window, 'chrome', {
                    get: () => ({
                        app: {
                            isInstalled: false,
                            InstallState: {DISABLED: "disabled", INSTALLED: "installed", NOT_INSTALLED: "not_installed"},
                            RunningState: {CANNOT_RUN: "cannot_run", READY_TO_RUN: "ready_to_run", RUNNING: "running"}
                        },
                        runtime: {
                            onConnect: null,
                            onMessage: null,
                            sendMessage: () => {},
                            connect: () => {},
                            onInstalled: {addListener: () => {}, removeListener: () => {}}
                        },
                        loadTimes: () => ({
                            requestTime: performance.now() * 0.001,
                            startLoadTime: performance.now() * 0.001,
                            commitLoadTime: performance.now() * 0.001,
                            finishDocumentLoadTime: performance.now() * 0.001,
                            finishLoadTime: performance.now() * 0.001,
                            firstPaintTime: performance.now() * 0.001,
                            firstPaintAfterLoadTime: 0,
                            navigationType: "Other"
                        }),
                        csi: () => ({
                            startE: performance.now(),
                            onloadT: performance.now(),
                            pageT: performance.now() * 0.001,
                            tran: 15
                        }),
                        webstore: {
                            onInstallStageChanged: {},
                            onDownloadProgress: {}
                        }
                    }),
                    configurable: false,
                    enumerable: true
                });
            }
            
            // === 第四层：权限API伪装 ===
            
            const originalQuery = window.navigator.permissions.query;
            Object.defineProperty(navigator.permissions, 'query', {
                value: (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({state: Notification.permission}) :
                        originalQuery(parameters)
                ),
                configurable: false
            });
            
            // === 第五层：深度检测对抗 ===
            
            // 伪装 getBattery API
            if (!navigator.getBattery) {
                Object.defineProperty(navigator, 'getBattery', {
                    value: () => Promise.resolve({
                        charging: true,
                        chargingTime: 0,
                        dischargingTime: Infinity,
                        level: 1,
                        addEventListener: () => {},
                        removeEventListener: () => {},
                        onchargingchange: null,
                        onchargingtimechange: null,
                        ondischargingtimechange: null,
                        onlevelchange: null
                    }),
                    configurable: false
                });
            }
            
            // 伪装 mediaDevices
            if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
                const originalEnumerateDevices = navigator.mediaDevices.enumerateDevices;
                Object.defineProperty(navigator.mediaDevices, 'enumerateDevices', {
                    value: () => originalEnumerateDevices.call(navigator.mediaDevices).then(devices => {
                        return devices.map(device => ({
                            deviceId: device.deviceId,
                            kind: device.kind,
                            label: device.label,
                            groupId: device.groupId
                        }));
                    }),
                    configurable: false
                });
            }
            
            // === 第六层：WebGL指纹对抗 ===
            
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) { // UNMASKED_VENDOR_WEBGL
                    return 'Intel Inc.';
                }
                if (parameter === 37446) { // UNMASKED_RENDERER_WEBGL
                    return 'Intel Iris OpenGL Engine';
                }
                return getParameter.call(this, parameter);
            };
            
            // === 第七层：时区和语言环境完整伪装 ===
            
            Object.defineProperty(Intl.DateTimeFormat.prototype, 'resolvedOptions', {
                value: function() {
                    return {
                        locale: 'zh-CN',
                        calendar: 'gregory',
                        numberingSystem: 'latn',
                        timeZone: 'Asia/Shanghai',
                        year: 'numeric',
                        month: 'numeric',
                        day: 'numeric'
                    };
                },
                configurable: false
            });
            
            // === 第八层：iframe检测对抗 ===
            
            Object.defineProperty(window, 'outerHeight', {
                get: () => window.innerHeight,
                configurable: false
            });
            
            Object.defineProperty(window, 'outerWidth', {
                get: () => window.innerWidth,
                configurable: false
            });
            
            // === 第九层：自动化工具特征清除 ===
            
            // 清除可能的Playwright特征
            delete window.__playwright;
            delete window.__pw_manual;
            delete window.__PW_inspect;
            
            // 清除可能的Selenium特征
            delete window._Selenium_IDE_Recorder;
            delete window._selenium;
            delete window.__selenium_evaluator;
            delete window.selenium;
            
            // 清除可能的Puppeteer特征  
            delete window.__puppeteer;
            delete window._puppeteer;
            
            // === 第十层：最终防护层 ===
            
            // 防止特征检测脚本修改我们的伪装
            const originalDefineProperty = Object.defineProperty;
            Object.defineProperty = function(obj, prop, descriptor) {
                if (obj === navigator && (prop === 'webdriver' || prop === 'plugins' || prop === 'languages')) {
                    return obj;
                }
                return originalDefineProperty.call(this, obj, prop, descriptor);
            };
            
            console.log('🔒 超强反检测脚本已注入完成');
        }
        """
        
        try:
            await self.main_page.add_init_script(stealth_script)
            logger.info("超强反检测脚本注入成功")
        except Exception as e:
            logger.warning(f"注入超强反检测脚本失败: {str(e)}")
    
    async def _handle_singleton_conflict(self):
        """处理浏览器实例冲突"""
        import os
        import shutil
        import psutil
        import subprocess
        
        try:
            logger.info("开始处理浏览器实例冲突...")
            
            # 1. 强制杀死所有相关的Chromium进程
            try:
                # 查找并终止所有与redbook_mcp相关的Chromium进程
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        cmdline = proc.info.get('cmdline', [])
                        cmdline_str = ' '.join(cmdline) if cmdline else ''
                        
                        # 匹配与当前项目相关的浏览器进程
                        if ('chromium' in proc.info['name'].lower() or 'chrome' in proc.info['name'].lower()) and 'redbook_mcp' in cmdline_str:
                            logger.info(f"终止冲突的浏览器进程: PID {proc.info['pid']}")
                            psutil.Process(proc.info['pid']).terminate()
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        pass
                
                # 等待进程完全终止
                await asyncio.sleep(2)
            except Exception as e:
                logger.warning(f"强制杀死浏览器进程时出错: {str(e)}")
            
            # 2. 清理锁文件
            try:
                lock_files = ["SingletonLock", "SingletonSocket", "SingletonCookie"]
                for lock_file in lock_files:
                    lock_path = os.path.join(BROWSER_DATA_DIR, lock_file)
                    if os.path.exists(lock_path):
                        if os.path.isfile(lock_path):
                            os.remove(lock_path)
                        elif os.path.isdir(lock_path):
                            shutil.rmtree(lock_path)
                        logger.info(f"清理了{lock_file}文件")
            except Exception as e:
                logger.warning(f"清理浏览器锁文件时出错: {str(e)}")
            
            # 3. 重置浏览器数据目录权限
            try:
                # 在Unix系统上重置权限
                if os.name == 'posix':
                    os.system(f"chmod -R 755 {BROWSER_DATA_DIR}")
                    logger.info("重置了浏览器数据目录权限")
            except Exception as e:
                logger.warning(f"重置浏览器数据目录权限时出错: {str(e)}")
            
            # 4. 清理可能的孤立进程
            try:
                if os.name == 'posix':  # macOS/Linux
                    subprocess.run(['pkill', '-f', 'chromium.*redbook_mcp'], stderr=subprocess.PIPE)
                elif os.name == 'nt':   # Windows
                    subprocess.run(['taskkill', '/f', '/im', 'chrome.exe'], stderr=subprocess.PIPE)
            except Exception as e:
                logger.warning(f"清理孤立进程时出错: {str(e)}")
            
            # 等待所有清理操作完成
            await asyncio.sleep(1)
            
            logger.info("浏览器实例冲突处理完成")
        except Exception as e:
            logger.warning(f"处理浏览器实例冲突时出错: {str(e)}")
    
    async def _check_login_status(self):
        """检查登录状态
        
        Returns:
            bool: 是否已登录
        """
        try:
            # 仅访问首页检查登录状态
            if not self.main_page.url.startswith("https://www.xiaohongshu.com"):
                await self.main_page.goto("https://www.xiaohongshu.com", timeout=DEFAULT_TIMEOUT)
                await asyncio.sleep(DEFAULT_WAIT_TIME)
            
            # 检查是否已登录
            login_elements = await self.main_page.query_selector_all('text="登录"')
            if login_elements:
                self.is_logged_in = False
                return False  # 需要登录
            else:
                self.is_logged_in = True
                return True  # 已登录
                
        except Exception as e:
            logger.warning(f"检查登录状态失败: {str(e)}")
            return False
    
    async def login(self):
        """登录小红书账号，使用智能登录管理器"""
        try:
            logger.info("开始登录流程...")
            
            # 使用智能登录管理器
            result = await self.login_manager.smart_login()
            
            # 如果登录成功，更新浏览器状态
            if "成功" in result or "已登录" in result or "已自动恢复" in result:
                self.is_logged_in = True
                logger.info("登录流程完成，状态已更新")
            else:
                self.is_logged_in = False
                logger.warning("登录流程完成，但未成功登录")
            
            return result
            
        except Exception as e:
            error_msg = f"登录过程出错: {str(e)}"
            logger.error(error_msg)
            self.is_logged_in = False
            return error_msg
    
    async def goto(self, url, wait_time=DEFAULT_WAIT_TIME, max_retries=2):
        """访问指定URL并等待加载完成，使用智能重试机制
        
        Args:
            url: 目标URL
            wait_time: 等待时间
            max_retries: 最大重试次数
        """
        # 优化：减少ensure_browser调用频率
        if not self._browser_healthy:
            await self.ensure_browser()
        
        for attempt in range(max_retries + 1):
            try:
                await self.main_page.goto(url, timeout=DEFAULT_TIMEOUT)
                await asyncio.sleep(wait_time)  # 等待页面加载
                
                # 检查是否出现登录弹窗或登录提示
                await self._handle_login_popup()
                
                logger.info(f"成功访问页面: {url}")
                return True
                
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"访问页面失败 (尝试 {attempt + 1}/{max_retries + 1}): {error_msg}")
                
                # 优化：分级错误处理
                if "timeout" in error_msg.lower():
                    # 超时错误：延长等待时间重试
                    if attempt < max_retries:
                        await asyncio.sleep(2)
                        continue
                        
                elif "closed" in error_msg.lower() or "disconnected" in error_msg.lower():
                    # 连接错误：标记为不健康，触发恢复
                    self._browser_healthy = False
                    if attempt < max_retries:
                        await self.ensure_browser(force_check=True)
                        continue
                        
                elif "navigation" in error_msg.lower():
                    # 导航错误：可能是页面问题，直接重试
                    if attempt < max_retries:
                        await asyncio.sleep(1)
                        continue
                        
                else:
                    # 其他错误：根据严重程度决定是否重试
                    if attempt < max_retries:
                        await asyncio.sleep(1)
                        continue
                
                # 所有重试都失败
                if attempt == max_retries:
                    logger.error(f"访问页面最终失败: {url}")
                    return False
        
        return False
    
    async def execute_scroll_script(self, script=None):
        """执行滚动脚本以加载更多内容
        
        Args:
            script (str, optional): 自定义滚动脚本. 默认为None.
        """
        if script is None:
            script = '''
                () => {
                    // 先滚动到页面底部
                    window.scrollTo(0, document.body.scrollHeight);
                    setTimeout(() => { 
                        // 然后滚动到中间
                        window.scrollTo(0, document.body.scrollHeight / 2); 
                    }, 1000);
                    setTimeout(() => { 
                        // 最后回到顶部
                        window.scrollTo(0, 0); 
                    }, 2000);
                }
            '''
        
        try:
            await self.main_page.evaluate(script)
            await asyncio.sleep(3)  # 等待滚动完成和内容加载
        except Exception as e:
            logger.warning(f"执行滚动脚本失败: {str(e)}")
    
    async def get_page_content(self):
        """获取当前页面内容
        
        Returns:
            str: 页面HTML内容
        """
        try:
            return await self.main_page.content()
        except Exception as e:
            logger.error(f"获取页面内容失败: {str(e)}")
            return ""
    
    async def _handle_login_popup(self):
        """处理页面上可能出现的登录弹窗
        
        Returns:
            bool: 是否处理了登录弹窗
        """
        try:
            # 检查是否出现登录弹窗或登录按钮
            login_elements = await self.main_page.query_selector_all('text="登录"')
            if login_elements and not self.is_logged_in:
                # 需要登录，执行登录流程
                await self.login()
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"处理登录弹窗失败: {str(e)}")
            return False
        
    async def close(self):
        """关闭浏览器并清理资源"""
        import os
        import psutil
        import subprocess
        
        try:
            logger.info("执行浏览器关闭")
            
            # 1. 尝试正常关闭浏览器上下文
            if self.browser_context:
                try:
                    await self.browser_context.close()
                    logger.info("浏览器上下文正常关闭")
                except Exception as e:
                    logger.warning(f"关闭浏览器上下文时出错: {str(e)}")
            
            # 2. 停止Playwright实例
            if self.playwright_instance:
                try:
                    await self.playwright_instance.stop()
                    logger.info("Playwright实例停止")
                except Exception as e:
                    logger.warning(f"停止Playwright实例时出错: {str(e)}")
            
            # 3. 强制清理浏览器进程（确保完全释放）
            try:
                # 查找并终止所有与redbook_mcp相关的Chromium进程
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        cmdline = proc.info.get('cmdline', [])
                        cmdline_str = ' '.join(cmdline) if cmdline else ''
                        
                        if ('chromium' in proc.info['name'].lower() or 'chrome' in proc.info['name'].lower()) and 'redbook_mcp' in cmdline_str:
                            logger.info(f"终止剩余的浏览器进程: PID {proc.info['pid']}")
                            psutil.Process(proc.info['pid']).terminate()
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        pass
                
                # 使用系统命令进行最终清理（以防有进程未被正确终止）
                if os.name == 'posix':  # macOS/Linux
                    subprocess.run(['pkill', '-f', 'chromium.*redbook_mcp'], stderr=subprocess.PIPE)
                elif os.name == 'nt':   # Windows
                    subprocess.run(['taskkill', '/f', '/im', 'chrome.exe'], stderr=subprocess.PIPE)
            except Exception as e:
                logger.warning(f"强制清理浏览器进程时出错: {str(e)}")
                
            # 4. 清理锁文件
            try:
                import shutil
                lock_files = ["SingletonLock", "SingletonSocket", "SingletonCookie"]
                for lock_file in lock_files:
                    lock_path = os.path.join(BROWSER_DATA_DIR, lock_file)
                    if os.path.exists(lock_path):
                        if os.path.isfile(lock_path):
                            os.remove(lock_path)
                        elif os.path.isdir(lock_path):
                            shutil.rmtree(lock_path)
                        logger.info(f"清理了{lock_file}文件")
            except Exception as e:
                logger.warning(f"清理锁文件时出错: {str(e)}")
                
            # 重置状态
            self.main_page = None
            self.browser_context = None
            self.playwright_instance = None
            self.is_logged_in = False
            self._browser_healthy = False
            
            # 额外等待确保资源完全释放
            await asyncio.sleep(1)
            
            logger.info("浏览器资源清理完成")
            
        except Exception as e:
            logger.error(f"关闭浏览器失败: {str(e)}")
            # 即使关闭失败，也要重置状态
            self.browser_context = None
            self.playwright_instance = None
            self.main_page = None
            self.is_logged_in = False
            self._browser_healthy = False
    
    def get_health_stats(self):
        """获取浏览器健康状态统计"""
        return {
            "healthy": self._browser_healthy,
            "restart_count": len(self.restart_timestamps),
            "last_health_check": self.last_health_check,
            "logged_in": self.is_logged_in
        }
    
    async def _hide_automation_bar(self):
        """强力隐藏所有类型的提示栏和警告信息"""
        hide_automation_css = """
        /* 最强力的隐藏策略 - 隐藏所有可能的提示栏 */
        
        /* 1. 通过文本内容隐藏 */
        *:has-text("Chrome 正受到自动测试软件的控制"),
        *:has-text("automated test software"),
        *:has-text("正受到自动测试软件的控制"),
        *:has-text("不受支持的命令行标记"),
        *:has-text("--no-sandbox"),
        *:has-text("--disable-blink-features"),
        *:has-text("AutomationControlled"),
        *:has-text("稳定性和安全性将会有所下降"),
        *:has-text("unsupported command-line flag"),
        *:has-text("stability and security will suffer"),
        *:has-text("命令行标记"),
        *:has-text("command-line flag"),
        
        /* 2. 通过元素属性隐藏 */
        [role="alert"],
        [role="alertdialog"],
        [data-testid*="infobar"],
        [data-testid*="alert"],
        [data-testid*="warning"],
        [class*="infobar"],
        [class*="alert"],
        [class*="warning"],
        [class*="automation"],
        [class*="security-state"],
        [class*="notification"],
        [id*="infobar"],
        [id*="alert"],
        [id*="warning"],
        [id*="automation"],
        [id*="security-state"],
        
        /* 3. Chrome特定元素 */
        chrome-infobar,
        .infobar,
        .security-state,
        .permission-bubble-view,
        .save-password-bubble-view,
        .translate-infobar,
        .one-click-signin-bubble,
        
        /* 4. 顶部固定的警告栏 */
        body > div[style*="position: fixed"][style*="top"],
        body > div[style*="position: absolute"][style*="top"],
        body > div[style*="z-index"][style*="background"],
        
        /* 5. 特定颜色的警告背景 */
        div[style*="background-color: rgb(255, 249, 196)"],
        div[style*="background-color: #fff9c4"],
        div[style*="background-color: rgb(255, 235, 59)"],
        div[style*="background-color: #ffeb3b"],
        div[style*="background-color: rgb(255, 193, 7)"],
        div[style*="background-color: #ffc107"],
        
        /* 6. 宽度跨越整个页面的顶部元素 */
        body > div:first-child[style*="width: 100%"],
        body > div:first-child[style*="left: 0"][style*="right: 0"],
        
        /* 7. 所有可能的浏览器UI元素 */
        [class*="browser-info"],
        [class*="page-info"],
        [class*="omnibox"],
        [data-automation-id],
        [data-test-automation] {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            height: 0 !important;
            width: 0 !important;
            max-height: 0 !important;
            max-width: 0 !important;
            overflow: hidden !important;
            position: fixed !important;
            top: -9999px !important;
            left: -9999px !important;
            z-index: -9999 !important;
            pointer-events: none !important;
            margin: 0 !important;
            padding: 0 !important;
            border: none !important;
            outline: none !important;
        }
        
        /* 8. 更激进的隐藏 - 基于内容模式 */
        div:contains("Chrome"),
        div:contains("自动"),
        div:contains("automation"),
        div:contains("controlled"),
        div:contains("软件"),
        div:contains("命令行"),
        div:contains("sandbox"),
        div:contains("blink-features"),
        div:contains("AutomationControlled"),
        div:contains("安全性"),
        div:contains("稳定性") {
            display: none !important;
        }
        
        /* 9. 隐藏任何包含警告关键词的父容器 */
        *:has(*:contains("Chrome 正受到")),
        *:has(*:contains("不受支持的命令行")),
        *:has(*:contains("disable-blink-features")) {
            display: none !important;
        }
        
        /* 10. 确保body顶部没有额外的间距 */
        body {
            padding-top: 0 !important;
            margin-top: 0 !important;
        }
        
        /* 11. 隐藏所有可能的notification区域 */
        [role="region"][aria-live],
        [aria-live="polite"],
        [aria-live="assertive"],
        .notification-area,
        .alert-area,
        #notification-area,
        #alert-area {
            display: none !important;
        }
        """
        
        try:
            await self.main_page.add_style_tag(content=hide_automation_css)
            
            # 额外的JavaScript隐藏脚本
            additional_hide_script = """
            () => {
                // 定期检查并隐藏任何新出现的警告元素
                const hideElements = () => {
                    // 隐藏包含特定文本的元素
                    const textToHide = [
                        'Chrome 正受到自动测试软件的控制',
                        'automated test software',
                        '不受支持的命令行标记',
                        '--no-sandbox',
                        '--disable-blink-features',
                        'AutomationControlled',
                        '稳定性和安全性将会有所下降',
                        'unsupported command-line flag',
                        'stability and security will suffer',
                        '命令行标记',
                        'command-line flag'
                    ];
                    
                    textToHide.forEach(text => {
                        const elements = Array.from(document.querySelectorAll('*')).filter(el => 
                            el.textContent && el.textContent.includes(text)
                        );
                        elements.forEach(el => {
                            el.style.display = 'none';
                            el.style.visibility = 'hidden';
                            el.style.opacity = '0';
                            el.style.position = 'fixed';
                            el.style.top = '-9999px';
                            el.style.left = '-9999px';
                            if (el.parentNode) {
                                el.parentNode.removeChild(el);
                            }
                        });
                    });
                    
                    // 隐藏所有role="alert"的元素
                    document.querySelectorAll('[role="alert"], [role="alertdialog"]').forEach(el => {
                        el.style.display = 'none';
                        el.style.visibility = 'hidden';
                        el.remove();
                    });
                };
                
                // 立即执行一次
                hideElements();
                
                // 每500ms检查一次
                setInterval(hideElements, 500);
                
                // 监听DOM变化
                const observer = new MutationObserver(hideElements);
                observer.observe(document.body, {
                    childList: true,
                    subtree: true,
                    attributes: true,
                    attributeFilter: ['style', 'class', 'id']
                });
            }
            """
            
            await self.main_page.evaluate(additional_hide_script)
            
            logger.info("已注入最强力的提示栏隐藏配置")
            
        except Exception as e:
            logger.warning(f"注入强力隐藏配置失败: {str(e)}")
