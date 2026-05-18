# Dữ liệu ngày tốt xấu âm lịch 1900-2200

Kho dữ liệu này chứa thông tin ngày tốt xấu, giờ hoàng đạo, giờ hắc đạo và các mục lịch âm được crawl từ các website tra cứu lịch âm Việt Nam.

Dữ liệu được chia theo năm trong thư mục `output_by_year/`, mỗi file JSON tương ứng một năm dương lịch. Kho hiện có 301 file cho giai đoạn 1900-2200, với tổng cộng 109.938 bản ghi ngày.

## Cấu trúc thư mục

```text
.
+-- crawl_xemlicham.py
+-- fill_empty_days_from_web.py
+-- output_by_year/
|   +-- du_lieu_ngay_tot_xau_1900.json
|   +-- du_lieu_ngay_tot_xau_1901.json
|   +-- ...
+-- README.md
```

Trong đó:

- `output_by_year/du_lieu_ngay_tot_xau_<nam>.json`: dữ liệu ngày tốt xấu theo từng năm dương lịch.
- `crawl_xemlicham.py`: script crawl dữ liệu ban đầu từ `xemlicham.com`.
- `fill_empty_days_from_web.py`: script bổ sung các ngày còn thiếu/rỗng bằng nguồn tham chiếu phụ.

## Định dạng dữ liệu

Mỗi file JSON là một object, trong đó key cấp cao nhất là ngày dương lịch theo định dạng `YYYY-MM-DD`. Giá trị của mỗi ngày là object gồm 11 trường văn bản.

Ví dụ rút gọn:

```json
{
  "1900-01-01": {
    "gio_hoang_dao": "...",
    "gio_hac_dao": "...",
    "cac_ngay_ky": "...",
    "ngu_hanh": "...",
    "banh_to_bach_ky_nhat": "...",
    "khong_minh_luc_dieu": "...",
    "nhi_thap_bat_tu": "...",
    "thap_nhi_kien_tru": "...",
    "ngoc_hap_thong_thu": "...",
    "huong_xuat_hanh": "...",
    "gio_xuat_hanh_theo_ly_thuan_phong": "..."
  }
}
```

## Giải thích các trường

| Trường | Ý nghĩa |
| --- | --- |
| `gio_hoang_dao` | Các khung giờ tốt trong ngày theo quan niệm lịch âm. |
| `gio_hac_dao` | Các khung giờ xấu/cần tránh trong ngày. |
| `cac_ngay_ky` | Các loại ngày kỵ nếu ngày đó phạm phải, ví dụ Tam Nương, Nguyệt Kỵ, Thọ Tử. |
| `ngu_hanh` | Thông tin can chi, nạp âm, hành ngày, tuổi xung/kỵ và quan hệ ngũ hành. |
| `banh_to_bach_ky_nhat` | Các câu Bành Tổ Bách Kỵ theo thiên can/địa chi của ngày. |
| `khong_minh_luc_dieu` | Phân loại ngày theo Khổng Minh Lục Diệu, gồm nhóm cát/hung và diễn giải. |
| `nhi_thap_bat_tu` | Thông tin 28 sao, việc nên làm, việc kiêng kỵ và ngoại lệ. |
| `thap_nhi_kien_tru` | Thông tin 12 trực, việc nên làm và không nên làm theo trực ngày. |
| `ngoc_hap_thong_thu` | Danh sách sao tốt, sao xấu và ý nghĩa liên quan. |
| `huong_xuat_hanh` | Hướng nên xuất hành để đón Hỷ Thần/Tài Thần và hướng nên tránh. |
| `gio_xuat_hanh_theo_ly_thuan_phong` | Diễn giải các khung giờ xuất hành theo Lý Thuần Phong. |

Tất cả các trường trên hiện được lưu dưới dạng chuỗi văn bản. Một số trường có nhiều dòng (`\n`) để giữ lại cấu trúc nội dung gốc.

## Nguồn dữ liệu

Nguồn chính:

- `xemlicham.com`
- Mẫu URL trong crawler: `https://www.xemlicham.com/am-lich/nam/{year}/thang/{month}/ngay/{day}`
- Ví dụ trang nguồn: <https://www.xemlicham.com/am-lich/nam/1900/thang/1/ngay/1>

Nguồn bổ sung khi bản ghi bị rỗng:

- `lichamngay.com`
- Mẫu URL trong script bổ sung: `https://lichamngay.com/nam-{year}/thang-{month}/lich-am-ngay-{day}-{month}-{year}.html`

Các script trong repo chỉ crawl và chuyển đổi nội dung công khai từ các trang trên thành JSON theo năm. Nếu bạn sử dụng lại dữ liệu, nên kiểm tra điều khoản sử dụng, bản quyền và chính sách robots/usage của từng website nguồn.


## Cách chạy crawler

Cài đặt các thư viện cần thiết:

```bash
pip install requests beautifulsoup4 tqdm
```

Chạy crawler:

```bash
python crawl_xemlicham.py
```

Bổ sung các ngày rỗng nếu cần:

```bash
python fill_empty_days_from_web.py
```

Lưu ý: crawler có delay, retry và phụ thuộc vào cấu trúc HTML của website nguồn. Nếu website thay đổi giao diện, parser có thể cần cập nhật.

## Chất lượng dữ liệu

Theo kiểm tra tại thời điểm tạo README:

- Giai đoạn dữ liệu: 1900-2200.
- Số file JSON theo năm: 301.
- Tổng số bản ghi ngày: 109.938.
- Không phát hiện bản ghi rỗng hoàn toàn theo 11 trường hiện tại.

Dữ liệu được tạo từ quá trình crawl và parse tự động, vì vậy vẫn có thể tồn tại sai sót do:

- Website nguồn thay đổi nội dung hoặc cấu trúc HTML.
- Lỗi mạng, timeout, redirect hoặc dữ liệu nguồn không đồng nhất.
- Lỗi tách section, map trường, làm sạch văn bản.
- Lỗi font/mã hóa tiếng Việt trong quá trình crawl, lưu file hoặc hiển thị.
- Khác biệt giữa các hệ thống lịch âm, lịch vạn niên và quan niệm dân gian.

## Miễn trừ trách nhiệm

Dữ liệu trong repo chỉ có mục đích tham khảo, nghiên cứu, học tập và phát triển phần mềm. Tác giả repo không cam kết dữ liệu là đầy đủ, chính xác tuyệt đối hoặc phù hợp cho mọi mục đích sử dụng.

Thông tin ngày tốt xấu, phong thủy, hướng xuất hành, giờ hoàng đạo/hắc đạo và các diễn giải liên quan là nội dung mang tính văn hóa, tín ngưỡng và tham khảo dân gian. Không nên xem đây là cơ sở duy nhất để đưa ra các quyết định quan trọng về pháp lý, tài chính, y tế, hôn nhân, xây dựng, kinh doanh hoặc các vấn đề có rủi ro cao.

Người sử dụng tự chịu trách nhiệm khi áp dụng, phân phối lại hoặc tích hợp dữ liệu này vào sản phẩm khác. Nếu phát hiện sai sót, vui lòng tạo issue hoặc pull request để cung cấp ngày/tháng/năm cụ thể và nội dung cần sửa.
