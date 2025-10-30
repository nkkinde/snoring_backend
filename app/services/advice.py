def build_advice(count: int, total_sec: int) -> str:
    if count <= 0:
        return "코골이가 감지되지 않았습니다. 오늘 수면 질은 전반적으로 양호합니다."
    msg = f"코골이 {count}회, 총 {total_sec}초 감지."
    tip = "옆으로 자기, 취침 전 음주/과식 피하기, 비강 가습을 고려해보세요. 지속되면 수면클리닉 상담을 권장합니다."
    return f"{msg} {tip}"
