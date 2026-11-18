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

### 使用账号或 Directus Token 登录

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

### 查看当前登录

```bash
linkseed auth whoami
```

这条命令不会把登录凭证打印出来。

### 退出登录

```bash
linkseed auth logout
```

退出后，这台电脑上的 linkseed 不再保持登录。服务地址会留下来，下次登录可以继续用。

## 使用 LinkSeed CLI

下表是全部命令。`< >` 里换成你自己的值。后面各节有完整说明。

| 命令 | 作用 |
| --- | --- |
| `linkseed auth login --username <用户名>` | 用账号登录。密码会单独询问。第一次还要加 `--base-url <地址>`。 |
| `linkseed auth login --directus-token` | 用后台访问令牌登录。令牌会单独询问。 |
| `linkseed auth whoami` | 查看当前登录的用户。不打印登录凭证。 |
| `linkseed auth logout` | 退出这台电脑上的登录。服务地址会保留。 |
| `linkseed activities list` | 列出学习活动。可按状态、模式、计划类型、关键词和更新时间筛选。 |
| `linkseed activities show <编号>` | 查看状态、点评和消息统计。加 `--messages` 看对话，再加 `--json` 可看笔迹坐标。 |
| `linkseed activities export <编号>` | 把这门课收成一份完整 Markdown。加 `--out <文件>` 则写入文件。 |
| `linkseed activities evaluation generate <编号>` | 生成或重新生成点评，并等到完成。加 `--no-wait` 则只提交、不等待。 |
| `linkseed activities evaluation edit <编号> --file <文件>` | 用文件里的文字修改已发布的点评。也可以从管道读入文字。 |
| `linkseed course snap <图片>` | 识别题目图片，不创建课程。`--out <文件>` 保存结果，`--create` 会在确认后建课。 |
| `linkseed course create --question-file <文件>` | 用识别结果建课。`--course-mode teaching` 是讲解课，`tutoring` 是辅导课。 |
| `linkseed course create --learning-plan-id <编号>` | 用已有学案开课。练习学案可选辅导课，微课学案只开讲解课。 |
| `linkseed course relearn <课程编号>` | 保留原来的课，并新开一门。 |

学习活动和建课命令需要先登录。除 `activities export` 外，这些命令都可以加 `--json`。管理员查看别人的活动时，在 `linkseed activities list` 后面加 `--user-id <用户编号>`。

### 查看学习活动

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

要把一门课收成一份完整的 Markdown，用 `export`。它和 `show` 看的是同一门课，但用途不同：`show` 在终端里翻看，对话默认只显示前 20 条，状态和对话要分两次看；`export` 自动翻完所有对话，和状态、统计、点评写在同一份里，适合保存或转给别人。

```bash
linkseed activities export 210
linkseed activities export 210 --out 210.md
```

不写 `--out` 时，Markdown 直接出现在终端里。写了 `--out` 时，内容进文件，终端只提示写入了哪个文件。

这份文件包含：

- 标题，以及课程编号、用户、状态、模式、学案类型、创建和更新时间
- 统计：消息、笔迹、语音、文字、系统异常
- 点评正文。没有点评时写「无点评。」生成失败时多一行错误说明
- 全部对话，按时间从早到晚。每条有时间、语音 / 笔迹 / 文字，学生说的话和老师的回复。笔迹只保留点数和图片地址

文件里没有笔迹坐标，也没有用量和内部诊断信息。要看坐标，仍用 `show 210 --messages --json`。

生成或重新生成点评：

```bash
linkseed activities evaluation generate 12
```

这条命令会等到点评完成。只有成功发布点评才返回退出码 `0`。生成失败、过期、归档或等待超时会返回 `1`，并在错误里写明原因。重新生成失败时，原来的点评仍然保留。如果只想提交、不等待，加上 `--no-wait`。

修改已发布的点评时，把新的文字放在文件里。程序会先读取当前点评，再保存：

```bash
linkseed activities evaluation edit 12 --file 点评.md
```

也可以把文字从管道传进去。管理员账号可以查看、生成和修改其他用户的活动，例如 `linkseed activities list --user-id 7`，然后对其中一门课执行 `evaluation generate` 或 `evaluation edit`。

### 从题目图片建课

先识别题目，确认之后再创建课程。识别不会创建课程。

```bash
linkseed course snap 题目.jpg --out question.json
linkseed course create --question-file question.json --course-mode teaching
```

把 `--course-mode` 换成 `tutoring` 就是辅导课。不写这个参数时按讲解课创建。讲解课还可以加 `--teaching-mode voice_only` 或 `voice_pen`；辅导课固定使用 `voice_pen`。

`snap` 会印出题干、公式、选项和图片地址。几何图看你提交的本地图片，以及摘要里的附件地址。觉得识别不对，就不要执行 `create`。要改识别结果，直接编辑 `question.json` 再创建。

在终端里也可以一次做完。程序会先问你是否创建：

```bash
linkseed course snap 题目.jpg --out question.json --create --course-mode teaching
```

已经有学案时，用学案编号开课。练习学案可以选辅导课。微课学案只开讲解课。

```bash
linkseed course create --learning-plan-id 88
```

重学会保留原来的课，并新开一门：

```bash
linkseed course relearn 172
```

创建或重学成功后，用印出的课程编号在 App 里打开这门课。这个编号也是 `linkseed activities show` 使用的编号。

### 登录信息存在哪里

请不要把这个文件发给别人，也不要把它放到网盘或聊天里。

- macOS：`/Users/你的用户名/.config/linkseed/config.toml`
- Windows：`C:\Users\你的用户名\.config\linkseed\config.toml`

### 命令执行失败时

失败时，终端的错误输出是一行说明，例如 `{"status": 401, "detail": "Invalid username or password."}`。`401` 表示用户名、密码或访问令牌不正确，或登录已经失效。`404` 表示活动或用户不存在，或者这门活动不属于当前账号。`403`、`409` 或 `422` 表示这次操作被拒绝、发生冲突，或内容不符合要求，例如课程不属于当前账号、一个后台账号对应了多个用户，或点评需要先刷新再保存。

程序的退出码：成功是 `0`；用户名、密码或令牌被拒绝是 `2`；找不到活动或用户是 `3`；操作被拒绝、冲突或内容不符合要求是 `4`；其他失败是 `1`。
