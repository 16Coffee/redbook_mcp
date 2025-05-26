#!/usr/bin/env node

/**
 * 自动安装脚本 - 在用户安装 npm 包后自动设置 Python 环境
 */

const { spawn, execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

const packageRoot = path.dirname(__dirname);

console.log('🔧 正在设置小红书 MCP 服务器...');

// 检查 Python 环境
async function checkPython() {
    const pythonCommands = ['python3', 'python'];
    
    for (const cmd of pythonCommands) {
        try {
            const version = execSync(`${cmd} --version`, { encoding: 'utf8', stdio: 'pipe' });
            const versionMatch = version.match(/Python (\d+)\.(\d+)/);
            
            if (versionMatch) {
                const major = parseInt(versionMatch[1]);
                const minor = parseInt(versionMatch[2]);
                
                if (major >= 3 && minor >= 8) {
                    console.log(`✅ 找到 Python ${version.trim()}`);
                    return cmd;
                }
            }
        } catch (error) {
            // 继续尝试下一个命令
        }
    }
    
    return null;
}

// 检查 pip
function checkPip(pythonCmd) {
    try {
        execSync(`${pythonCmd} -m pip --version`, { stdio: 'pipe' });
        return true;
    } catch (error) {
        return false;
    }
}

// 安装 Python 依赖
async function installPythonDeps(pythonCmd) {
    return new Promise((resolve, reject) => {
        console.log('📦 正在安装 Python 依赖...');
        
        const requirementsPath = path.join(packageRoot, 'requirements.txt');
        
        // 检查 requirements.txt 是否存在
        if (!fs.existsSync(requirementsPath)) {
            console.log('⚠️  requirements.txt 不存在，跳过 Python 依赖安装');
            resolve();
            return;
        }
        
        const pip = spawn(pythonCmd, ['-m', 'pip', 'install', '-r', requirementsPath], {
            stdio: 'inherit',
            cwd: packageRoot
        });
        
        pip.on('close', (code) => {
            if (code === 0) {
                console.log('✅ Python 依赖安装完成');
                resolve();
            } else {
                console.log('⚠️  Python 依赖安装失败，但不影响基本功能');
                resolve(); // 不阻止安装过程
            }
        });
        
        pip.on('error', (error) => {
            console.log('⚠️  Python 依赖安装出错，但不影响基本功能');
            resolve(); // 不阻止安装过程
        });
    });
}

// 创建配置文件
function createConfig() {
    const configDir = path.join(os.homedir(), '.xiaohongshu-mcp');
    const configFile = path.join(configDir, 'config.json');
    
    if (!fs.existsSync(configDir)) {
        fs.mkdirSync(configDir, { recursive: true });
    }
    
    if (!fs.existsSync(configFile)) {
        const defaultConfig = {
            version: require('../package.json').version,
            installPath: packageRoot,
            pythonCommand: 'python3',
            logLevel: 'INFO',
            dataDir: path.join(configDir, 'data'),
            firstRun: true
        };
        
        fs.writeFileSync(configFile, JSON.stringify(defaultConfig, null, 2));
        console.log(`✅ 配置文件已创建: ${configFile}`);
    }
}

// 创建数据目录
function createDataDir() {
    const configDir = path.join(os.homedir(), '.xiaohongshu-mcp');
    const dataDir = path.join(configDir, 'data');
    
    if (!fs.existsSync(dataDir)) {
        fs.mkdirSync(dataDir, { recursive: true });
        console.log(`✅ 数据目录已创建: ${dataDir}`);
    }
}

// 显示安装完成信息
function showCompletionMessage() {
    console.log(`
🎉 小红书 MCP 服务器安装完成！

📋 下一步：在 CherryStudio 中配置

1. 打开 CherryStudio
2. 进入设置 → MCP 服务器
3. 添加新服务器：

{
  "name": "小红书",
  "command": "xiaohongshu-mcp",
  "args": []
}

4. 重启 CherryStudio

🚀 然后你就可以在对话中使用小红书功能了！

💡 示例用法：
- "请帮我登录小红书"
- "搜索关于AI的笔记"
- "在这个笔记下发布评论：[笔记链接]"

📚 更多帮助：https://github.com/yourusername/xiaohongshu-mcp-server
`);
}

// 主安装流程
async function main() {
    try {
        // 检查 Python
        const pythonCmd = await checkPython();
        
        if (!pythonCmd) {
            console.log(`
⚠️  未找到 Python 3.8+ 环境

小红书 MCP 服务器需要 Python 3.8 或更高版本。

安装方法：
- macOS: brew install python3
- Windows: 从 python.org 下载安装
- Linux: sudo apt install python3 python3-pip

安装 Python 后，请重新运行：
npm install -g xiaohongshu-mcp-server
`);
            process.exit(1);
        }
        
        // 检查 pip
        if (!checkPip(pythonCmd)) {
            console.log('⚠️  pip 不可用，请安装 pip');
            process.exit(1);
        }
        
        // 更新配置中的 Python 命令
        createConfig();
        const configFile = path.join(os.homedir(), '.xiaohongshu-mcp', 'config.json');
        const config = JSON.parse(fs.readFileSync(configFile, 'utf8'));
        config.pythonCommand = pythonCmd;
        fs.writeFileSync(configFile, JSON.stringify(config, null, 2));
        
        // 安装 Python 依赖
        await installPythonDeps(pythonCmd);
        
        // 创建数据目录
        createDataDir();
        
        // 显示完成信息
        showCompletionMessage();
        
    } catch (error) {
        console.error('❌ 安装过程中出错:', error.message);
        console.log(`
如果问题持续存在，请：
1. 检查网络连接
2. 确保有足够的磁盘空间
3. 在 GitHub 上报告问题：https://github.com/yourusername/xiaohongshu-mcp-server/issues
`);
        process.exit(1);
    }
}

// 只在直接运行时执行
if (require.main === module) {
    main();
}

module.exports = { main };
