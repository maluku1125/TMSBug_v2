"""Discord ansi 碼塊的上色工具。

以前這些欄位用 ```ml / ```autohotkey / ```fix，靠語法高亮器去染「欄位名：」。
那是借來的顏色：高亮器一換版，配色就跟著變（2026-10 這次變成欄位名與數值
各自亂上色）。ansi 碼塊不經過高亮器，顏色是這裡寫死的，改版不會再動到它。

Discord 認得的 SGR 子集（2026-10 實測）：
    0 重設、1 粗體、3 斜體、4 底線、9 刪除線
    前景 30-37、背景 40-47、亮色 90-97
    256 色 38;5;N、48;5;N，全彩 38;2;R;G;B

256 色與全彩確實都會動（/ansitest 看過），但兩者都沒有官方文件、也只在
自己的客戶端驗過，不保證每個使用者吃得下 —— 吃不下的是把 `[38;5;208m`
原樣印出來，不是默默沒顏色，所以賭錯的代價不小。

因此骨幹顏色一律用存在很多年的 30-37 與 90-97；256 色只用在
C_DELTA 這種「退化成裸碼也只是醜一行、不影響讀懂數值」的點綴上。

字數：每染一段就多 11 個字元（一組顏色 + 一個重設）。embed 單一欄位上限
1024 字，整個 embed 6000 字 —— 行數多的欄位記得算一下。
"""
import re

ESC = '\u001b'

# 八色。名字比數字好讀，呼叫端不必記 34 是什麼。
GREY, RED, GREEN, YELLOW, BLUE, PINK, CYAN, WHITE = range(30, 38)

# 同樣八色的亮版（90-97）。深色主題下 34 的藍、35 的粉壓在碼塊的深底色上
# 不夠跳，要「一眼看到」的字一律改用亮版。這組跟 30-37 一樣是行之有年的
# 標準色，不是 38;2 全彩那種未公開功能，可以放心用。
(BRIGHT_GREY, BRIGHT_RED, BRIGHT_GREEN, BRIGHT_YELLOW,
 BRIGHT_BLUE, BRIGHT_PINK, BRIGHT_CYAN, BRIGHT_WHITE) = range(90, 98)


def c256(n: int) -> str:
    """256 色前景碼。回傳字串，paint() 的 f-string 直接接得上（`0;38;5;208`）。

    讀一下模組開頭那段警告再用：這組沒有官方文件，不支援的客戶端會把
    `[38;5;208m` 整串印出來。
    """
    return '38;5;%d' % n


# 紫色在 16 色裡沒有更亮的了（35 的亮版就是 95，使用者實測仍然偏深），
# 所以成長量改用 256 色的橘 —— /ansitest 的 38;5;208，暖色、在深色主題上
# 最跳，而且跟欄位名的藍完全分得開。
ORANGE = c256(208)

C_LABEL = BRIGHT_BLUE   # 冒號前的欄位名（冒號跟著它走）
C_VALUE = None          # 冒號後不上色，維持碼塊的預設字色（37 的白偏灰）
C_DELTA = ORANGE        # [+0.42%] 這種夾在數值裡的成長量

# 成長量只認中括號包起來的加號開頭，例如 [+0.42%]、[+5]。
# 不去比對裸的 `+5`，那種東西在數值裡太常見，會誤傷。
_DELTA = re.compile(r'\[\+[^\]]*\]')

SEP = '：'          # 全形冒號。版面對齊靠的就是它，半形的可能出現在數值裡


def paint(text: str, color: int | str | None) -> str:
    """整段上色。color 是 None 就原樣回傳，維持碼塊的預設字色。"""
    if color is None or not text:
        return text
    return f'{ESC}[0;{color}m{text}{ESC}[0m'


def bold(text: str) -> str:
    """粗體，不帶顏色。Discord 吃 SGR 1（2026-10 實測）。"""
    if not text:
        return text
    return f'{ESC}[1m{text}{ESC}[0m'


def paint_value(text: str, color: int | str | None = C_VALUE,
                delta: int | str | None = C_DELTA) -> str:
    """數值整段上 color，其中 [+…] 的部分改上 delta。

    每一段各自重設，所以不必擔心顏色互相汙染。
    """
    if delta is None:
        return paint(text, color)
    out, pos = [], 0
    for m in _DELTA.finditer(text):
        out.append(paint(text[pos:m.start()], color))
        out.append(paint(m.group(0), delta))
        pos = m.end()
    out.append(paint(text[pos:], color))
    return ''.join(out)


def kv(line: str, label: int | str | None = C_LABEL,
       value: int | str | None = C_VALUE,
       delta: int | str | None = C_DELTA, sep: str = SEP) -> str:
    """把「欄位名：數值」拆成兩段上色，冒號跟著欄位名走。

    整行沒有冒號時（分隔線、標題列）全部套欄位名那一段的顏色。
    """
    head, found, tail = line.partition(sep)
    if not found:
        return paint(line, label)
    return paint(head + sep, label) + paint_value(tail, value, delta)


def block(*groups, label: int | str | None = C_LABEL,
          value: int | str | None = C_VALUE,
          delta: int | str | None = C_DELTA, sep: str = SEP) -> str:
    """把一組或多組「欄位名：數值」接成一個 ansi 碼塊。

    groups 收的是字串清單；傳多組就接在一起，中間不插空行。
    """
    lines = [ln for g in groups for ln in g]
    body = '\n'.join(kv(ln, label, value, delta, sep) for ln in lines)
    return '```ansi\n' + body + '```'


def plain_block(text: str, color: int | str | None = None) -> str:
    """整塊就是一個值（沒有欄位名）的情境，例如「7日成長」只有一個百分比。"""
    return '```ansi\n' + paint(text, color) + '```'
