"""Editorial session labels; keep original source titles in verified records."""
import re


def session_title(title):
    """Translate only standalone session labels inside full/half-width parentheses."""
    def replace(match):
        label = match[3]
        if label == '上午場':
            label = '早起場'
        elif label == '下午場':
            label = '下晝場'
        else:
            number = label[1:-1]
            if number.isdecimal():
                value = int(number)
                digits = '零一二三四五六七八九'
                if 1 <= value < 10:
                    number = digits[value]
                elif 10 <= value < 100:
                    tens, ones = divmod(value, 10)
                    number = (digits[tens] if tens > 1 else '') + '十' + (digits[ones] if ones else '')
            label = '第' + number + '工'
        return match[1] + match[2] + label + match[4] + match[5]

    return re.sub(r'([（(])(\s*)(上午場|下午場|第(?:[0-9０-９]+|[一二三四五六七八九十百千零〇兩]+)日)(\s*)([）)])', replace, title)
