# linkseed

linkseed 是安装在电脑上的命令行程序，用来登录你的 Linkseed 账号。支持 macOS 和 Windows。安装完成后，在终端里输入 `linkseed` 即可使用，不需要再安装别的软件。

## 安装

macOS 打开「终端」，执行：

```bash
curl -fsSL https://raw.githubusercontent.com/linkseedai/cli/main/install.sh | sh
```

Windows 打开 PowerShell，执行：

```powershell
irm https://raw.githubusercontent.com/linkseedai/cli/main/install.ps1 | iex
```

装好之后，关掉终端再打开一次。输入 `linkseed auth --help` 能看到登录说明，就表示安装成功。

macOS 如果仍然提示找不到 `linkseed`，把下面这一行加进 `~/.zshrc`，保存后再打开一次终端：

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## 登录

服务地址以 `https://` 开头。用账号登录时不要把密码写在命令里，终端会单独询问，输入时不会显示：

```bash
linkseed auth login --base-url https://linkseedapi.lessonian.com --username 你的用户名
```

成功时会看到类似这样的一行：

```text
Logged in as user 7 (directus_link=active).
```

这里的数字是你的用户编号。`directus_link` 表示是否关联了后台账号：

| 显示 | 含义 |
| --- | --- |
| `active` | 已关联，后台账号可用 |
| `inactive` | 后台账号已停用 |
| `missing` | 原来的关联已经失效 |
| `unlinked` | 还没有关联后台账号 |

用密码登录大约 30 天后需要重新登录。这次登录不会让手机或电脑上的 Linkseed 应用退出。

如果你已经有后台的访问令牌，可以不输入密码。令牌同样不要写在命令里：

```bash
linkseed auth login --base-url https://linkseedapi.lessonian.com --directus-token
```

账号密码和访问令牌只能选一种。访问令牌过期后，用新的令牌或账号密码重新登录。登录结果里不会打印这张令牌。

第一次登录之后，同一台电脑上可以省略 `--base-url`。

## 查看当前登录

```bash
linkseed auth whoami
```

这条命令不会把登录凭证打印出来。

## 退出登录

```bash
linkseed auth logout
```

退出后，这台电脑上的 linkseed 不再保持登录。服务地址会留下来，下次登录可以继续用。

## 登录信息存在哪里

请不要把这个文件发给别人，也不要把它放到网盘或聊天里。

- macOS：`/Users/你的用户名/.config/linkseed/config.toml`
- Windows：`C:\Users\你的用户名\.config\linkseed\config.toml`

## 命令执行失败时

失败时，终端的错误输出是一行说明，例如 `{"status": 401, "detail": "Invalid username or password."}`。`401` 表示用户名、密码或访问令牌不正确，或登录已经失效。

程序的退出码：成功是 `0`；用户名、密码或令牌被拒绝是 `2`；这次登录无法完成（例如一个后台账号对应了多个用户）是 `4`；其他失败是 `1`。
