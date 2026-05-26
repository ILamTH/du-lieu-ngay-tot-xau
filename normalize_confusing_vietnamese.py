from __future__ import annotations

from pathlib import Path


OUTPUT_DIR = Path("output_by_year")


REPLACEMENTS = {
    "Ngày này trăm sự đều kỵ không nên tiến hành bất cứ việc gì.": (
        "Theo quan niệm dân gian, ngày này rất kỵ; nên hạn chế tiến hành các việc quan trọng."
    ),
    "Mất tiền, mất của nếu đi hướng Nam thì tìm nhanh mới thấy.": (
        "Nếu bị mất tiền hoặc tài sản, đi về hướng Nam thì có thể dễ tìm thấy hơn."
    ),
    "Đề phòng tranh cãi, mâu thuẫn hay miệng tiếng tầm thường.": (
        "Đề phòng tranh cãi, mâu thuẫn hoặc điều tiếng không đáng có."
    ),
    "Việc làm chậm, lâu la nhưng tốt nhất làm việc gì đều cần chắc chắn.": (
        "Công việc dễ chậm trễ; làm việc gì cũng nên chuẩn bị chắc chắn."
    ),
    "Hay tranh luận, cãi cọ, gây chuyện đói kém, phải đề phòng.": (
        "Dễ phát sinh tranh luận, cãi cọ hoặc chuyện bất lợi; nên thận trọng."
    ),
    "Phòng người người nguyền rủa, tránh lây bệnh.": (
        "Đề phòng điều tiếng, lời trách móc và chú ý giữ gìn sức khỏe."
    ),
    "Nói chung những việc như hội họp, tranh luận, việc quan,…nên tránh đi vào giờ này.": (
        "Những việc như hội họp, tranh luận hoặc việc liên quan đến công quyền nên tránh thực hiện vào giờ này."
    ),
    "Nếu bắt buộc phải đi vào giờ này thì nên giữ miệng để hạn ché gây ẩu đả hay cãi nhau.": (
        "Nếu bắt buộc phải đi vào giờ này thì nên giữ lời nói chừng mực để tránh ẩu đả hoặc cãi vã."
    ),
    "Nếu có bệnh cầu thì sẽ khỏi, gia đình đều mạnh khỏe.": (
        "Nếu cầu chữa bệnh thì có thể gặp thuận lợi; gia đình được bình an, khỏe mạnh."
    ),
    "Nếu ra đi hay thiệt, gặp nạn, việc quan trọng thì phải đòn, gặp ma quỷ nên cúng tế thì mới an.": (
        "Nếu xuất hành dễ gặp bất lợi hoặc rủi ro; việc quan trọng nên thận trọng, chuẩn bị kỹ và cân nhắc lễ nghi theo tín ngưỡng nếu cần."
    ),
    "Trong này Tiểu Cát mọi việc đều tốt lành và ít gặp trở ngại.": (
        "Ngày Tiểu Cát thường được xem là tốt lành, mọi việc ít gặp trở ngại."
    ),
    "Mưu đại sự hanh thông, thuận lợi, cùng với đó âm phúc độ trì, che chở, được quý nhân nâng đỡ.": (
        "Việc lớn có thể thuận lợi, được phúc đức che chở và có quý nhân giúp đỡ."
    ),
    "Không nên ăn chó, quỉ quái lên giường": (
        "Không nên sát sinh hoặc ăn thịt chó; theo quan niệm cũ có thể gặp điều không lành trong nhà"
    ),
    "Không nên tiến hành các việc đi nhận quan để tránh việc gia chủ sẽ không hồi hương": (
        "Không nên nhận chức hoặc nhận nhiệm vụ xa nhà; theo quan niệm cũ dễ gặp trở ngại khi trở về"
    ),
    "Động đất, ban nền đắp nền": "Động thổ, san nền, đắp nền",
    "Khởi công trăm việc đều đặng tốt.": (
        "Khởi công nhiều việc đều được xem là tốt."
    ),
    "Công việc dây dưa khó thành, cầu tài mờ mịt.": (
        "Công việc dễ kéo dài, khó thành; cầu tài chưa rõ ràng."
    ),
    "Hay xảy ra cãi cọ, nên giữ mồm giữ miệng.": (
        "Dễ xảy ra cãi cọ, nên giữ lời nói chừng mực."
    ),
    "Giờ Tiểu Các": "Giờ Tiểu Cát",
    "Mọi việc không may, cầu tài không có lợi, hay bị trái ý, đi xa e gặp nạn, tranh chấp thua thiệt đuối lý. Việc quan trọng phải đòn.": (
        "Mọi việc dễ gặp bất lợi, cầu tài không thuận, dễ trái ý; đi xa hoặc tranh chấp nên thận trọng. Việc quan trọng cần chuẩn bị kỹ."
    ),
    "Tránh xuất hành hướng Lên Trời gặp Hạc Thần (xấu)": (
        "Hạc Thần là sao xấu, nhưng ngày này Hạc Thần ở trên trời nên không xác định hướng cụ thể để tránh."
    ),
    r"\n-\n": (
        r"\n- "
    ),
    r"\n:": (
        r":"
    )
}


def main() -> None:
    changed_files = 0
    total_replacements = 0

    for path in sorted(OUTPUT_DIR.glob("*.json")):
        print(path)
        text = path.read_text(encoding="utf-8")
        original = text
        file_replacements = 0

        for old, new in REPLACEMENTS.items():
            count = text.count(old)
            if count:
                text = text.replace(old, new)
                file_replacements += count

        if text != original:
            path.write_text(text, encoding="utf-8")
            changed_files += 1
            total_replacements += file_replacements

    print(f"Changed files: {changed_files}")
    print(f"Total replacements: {total_replacements}")


if __name__ == "__main__":
    main()
