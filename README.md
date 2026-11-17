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

## 查看学习活动

登录之后可以查看自己的学习活动。活动编号在列表的第一列。

```bash
linkseed activities list
linkseed activities show 12
linkseed activities show 12 --messages
```

`list` 可以按状态、模式、计划类型和更新时间筛选，例如：

```bash
linkseed activities list --status completed --query 分数 --limit 20
```

`show` 显示活动状态、点评，以及消息统计：总消息数、笔迹数、语音数、文字数、系统异常数。既用手写又用语音的一条消息，会计入笔迹，也会计入语音。

要看这门课里的消息，加上 `--messages`。默认是前 20 条，用 `--limit` 和 `--offset` 翻页。每条会标出语音、笔迹、文字或系统异常。笔迹只显示点数和图片地址。

```bash
linkseed activities show 210 --messages
linkseed activities show 210 --messages --offset 20
```

要连笔迹坐标一起看，加上 `--json`。带坐标时一页最多 20 条：

```bash
linkseed activities show 210 --messages --json
```

生成或重新生成点评：

```bash
linkseed activities evaluation generate 12
```

这条命令会等到点评完成。只有成功发布点评才返回退出码 `0`。生成失败、过期、归档或等待超时会返回 `1`，并在错误里写明原因。重新生成失败时，原来的点评仍然保留。如果只想提交、不等待，加上 `--no-wait`。

修改已发布的点评时，把新的文字放在文件里。程序会先读取当前点评，再保存：

```bash
linkseed activities evaluation edit 12 --file 点评.md
```

也可以把文字从管道传进去。管理员账号可以查看其他用户的活动，例如 `linkseed activities list --user-id 7`。生成和修改点评仍然只能针对自己的活动。

## 登录信息存在哪里

请不要把这个文件发给别人，也不要把它放到网盘或聊天里。

- macOS：`/Users/你的用户名/.config/linkseed/config.toml`
- Windows：`C:\Users\你的用户名\.config\linkseed\config.toml`

## 命令执行失败时

失败时，终端的错误输出是一行说明，例如 `{"status": 401, "detail": "Invalid username or password."}`。`401` 表示用户名、密码或访问令牌不正确，或登录已经失效。`404` 表示活动或用户不存在，或者这门活动不属于当前账号。`409` 或 `422` 表示这次操作冲突或内容不符合要求，例如一个后台账号对应了多个用户，或点评需要先刷新再保存。

程序的退出码：成功是 `0`；用户名、密码或令牌被拒绝是 `2`；找不到活动或用户是 `3`；操作冲突或内容不符合要求是 `4`；其他失败是 `1`。
