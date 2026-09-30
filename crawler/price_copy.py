"""Fill missing OPENTIX price labels using the site's existing wording."""
import re


def complete(prices, activities):
    result = dict(prices)
    for activity in activities:
        original = activity.get('price_info', '')
        if original in result:
            continue
        match = re.fullmatch(
            r'票面價格：([0-9、.]+)元；折扣、贊助票與購票條件依官方頁面'
            r'(；免費票適用資格未確認，請洽主辦單位)?', original)
        if match:
            result[original] = '票價：' + match[1] + '元；折扣、贊助票佮買票規定，請看官方公告。'
            if match[2]:
                result[original] += '免費票的資格猶未確認，請問主辦單位。'
    return result
