# Dữ liệu ngày tốt xấu âm lịch Việt Nam 1900-2200

Kho dữ liệu này cung cấp bộ JSON tra cứu ngày tốt/xấu theo lịch âm Việt Nam cho toàn bộ giai đoạn **1900-2200**. Dữ liệu được tổ chức theo năm và theo từng ngày để có thể dùng trực tiếp như một API tĩnh trong ứng dụng web/mobile, công cụ tra cứu lịch, dashboard nội bộ hoặc các tác vụ phân tích dữ liệu.

Bộ dữ liệu hiện có:

- **301** file JSON theo năm trong `output_by_year/`.
- **109.938** file JSON theo ngày trong `output_by_date/`.
- **109.938** bản ghi ngày, phủ đủ mọi ngày dương lịch từ `1900-01-01` đến `2200-12-31`.

> Lưu ý: nội dung ngày tốt/xấu, giờ hoàng đạo, phong thủy và xuất hành là thông tin văn hóa/tín ngưỡng dân gian, chỉ nên dùng để tham khảo.

## Mục lục

- [Cấu trúc repository](#cấu-trúc-repository)
- [Định dạng dữ liệu](#định-dạng-dữ-liệu)
- [Giải thích các trường](#giải-thích-các-trường)
- [Sử dụng như API tĩnh](#sử-dụng-như-api-tĩnh)
- [Ví dụ tích hợp](#ví-dụ-tích-hợp)
- [Nguồn dữ liệu và quy trình xử lý](#nguồn-dữ-liệu-và-quy-trình-xử-lý)
- [Cài đặt môi trường](#cài-đặt-môi-trường)
- [Các script trong repo](#các-script-trong-repo)
- [Quy trình tái tạo/cập nhật dữ liệu](#quy-trình-tái-tạocập-nhật-dữ-liệu)
- [Kiểm tra chất lượng dữ liệu](#kiểm-tra-chất-lượng-dữ-liệu)
- [Lưu ý sử dụng và miễn trừ trách nhiệm](#lưu-ý-sử-dụng-và-miễn-trừ-trách-nhiệm)
- [Đóng góp](#đóng-góp)

## Cấu trúc repository

```text
.
├── crawl_xemlicham.py
├── enrich_day_quality_can_chi.py
├── fill_empty_days_from_web.py
├── normalize_confusing_vietnamese.py
├── split_by_date.py
├── output_by_year/
│   ├── du_lieu_ngay_tot_xau_1900.json
│   ├── du_lieu_ngay_tot_xau_1901.json
│   └── ...
├── output_by_date/
│   ├── 1900/
│   │   ├── 01/
│   │   │   ├── 01.json
│   │   │   └── ...
│   │   └── ...
│   └── ...
├── LICENSE
└── README.md
```

| Đường dẫn | Vai trò |
| --- | --- |
| `output_by_year/du_lieu_ngay_tot_xau_<nam>.json` | Dữ liệu theo từng năm dương lịch, root JSON là object có key `YYYY-MM-DD`. |
| `output_by_date/<nam>/<thang>/<ngay>.json` | Dữ liệu theo từng ngày, root JSON là object bản ghi của ngày đó. |
| `crawl_xemlicham.py` | Crawl dữ liệu ban đầu từ `xemlicham.com`, có delay, retry và checkpoint. |
| `fill_empty_days_from_web.py` | Bổ sung các ngày bị rỗng bằng nguồn phụ `lichamngay.com` và ghi log JSONL. |
| `normalize_confusing_vietnamese.py` | Chuẩn hóa một số câu tiếng Việt cổ/tối nghĩa/lỗi chính tả trong dữ liệu JSON. |
| `enrich_day_quality_can_chi.py` | Enrich thêm `day_quality` và `can_chi` từ trang tháng/ngày của `xemlicham.com`. |
| `split_by_date.py` | Tách dữ liệu từ `output_by_year/` sang `output_by_date/`. |

## Định dạng dữ liệu

### File theo năm

Mỗi file trong `output_by_year/` là một object. Key cấp cao nhất là ngày dương lịch theo định dạng `YYYY-MM-DD`; value là object dữ liệu ngày.

Ví dụ rút gọn:

```json
{
  "2025-01-01": {
    "gio_hoang_dao": "Tí (23:00-0:59) ; Sửu (1:00-2:59) ; ...",
    "gio_hac_dao": "Dần (3:00-4:59) ; Thìn (7:00-8:59) ; ...",
    "cac_ngay_ky": "Phạm phải ngày:\n- Kim Thần Thất Sát: ...",
    "ngu_hanh": "Ngày:\nCanh Ngọ\n- tức Chi khắc Can ...",
    "banh_to_bach_ky_nhat": "Canh: ...\n- Ngọ: ...",
    "khong_minh_luc_dieu": "Ngày:\nLưu Liên\n- tức ngày Hung...",
    "nhi_thap_bat_tu": "Tên sao: Sao Sâm\nTên ngày: ...",
    "thap_nhi_kien_tru": "Trực Chấp\nNên làm: ...",
    "ngoc_hap_thong_thu": "Sao tốt:\n- Thiên Đức: ...\nSao xấu:\n- ...",
    "huong_xuat_hanh": "Hỷ thần: ...\nTài thần: ...",
    "gio_xuat_hanh_theo_ly_thuan_phong": "23h-01h và 11h-13h: ...",
    "day_quality": "good",
    "can_chi": {
      "ngay": "Canh Ngọ",
      "thang": "Bính Tý",
      "nam": "Giáp Thìn"
    }
  }
}
```

### File theo ngày

Mỗi file trong `output_by_date/` chỉ chứa trực tiếp object dữ liệu ngày, không bọc thêm key `YYYY-MM-DD`.

Ví dụ đường dẫn:

```text
output_by_date/2025/01/01.json
```

Ví dụ rút gọn:

```json
{
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
  "gio_xuat_hanh_theo_ly_thuan_phong": "...",
  "day_quality": "good",
  "can_chi": {
    "ngay": "Canh Ngọ",
    "thang": "Bính Tý",
    "nam": "Giáp Thìn"
  }
}
```

## Giải thích các trường

| Trường | Kiểu | Ý nghĩa |
| --- | --- | --- |
| `gio_hoang_dao` | `string` | Các khung giờ hoàng đạo/tốt trong ngày theo quan niệm lịch âm. |
| `gio_hac_dao` | `string` | Các khung giờ hắc đạo/xấu hoặc nên tránh trong ngày. |
| `cac_ngay_ky` | `string` | Các loại ngày kỵ nếu ngày đó phạm phải, ví dụ Tam Nương, Nguyệt Kỵ, Thọ Tử, Kim Thần Thất Sát. |
| `ngu_hanh` | `string` | Diễn giải can chi ngày, quan hệ can/chi, nạp âm, hành ngày, tuổi kỵ/xung/hợp. |
| `banh_to_bach_ky_nhat` | `string` | Các câu Bành Tổ Bách Kỵ ứng với thiên can và địa chi của ngày. |
| `khong_minh_luc_dieu` | `string` | Phân loại ngày theo Khổng Minh Lục Diệu và phần diễn giải cát/hung. |
| `nhi_thap_bat_tu` | `string` | Thông tin Nhị Thập Bát Tú: tên sao, tên ngày, việc nên làm, kiêng cữ và ngoại lệ. |
| `thap_nhi_kien_tru` | `string` | Thông tin Thập Nhị Kiến Trừ/12 trực: trực ngày, việc nên làm và không nên làm. |
| `ngoc_hap_thong_thu` | `string` | Danh sách sao tốt, sao xấu theo Ngọc Hạp Thông Thư và ý nghĩa liên quan. |
| `huong_xuat_hanh` | `string` | Hướng xuất hành nên đi/không nên đi để đón Hỷ Thần, Tài Thần hoặc tránh Hạc Thần. |
| `gio_xuat_hanh_theo_ly_thuan_phong` | `string` | Diễn giải các khung giờ xuất hành theo Lý Thuần Phong. |
| `day_quality` | `string` | Phân loại tổng quát theo trang tháng: `good` = ngày tốt/Hoàng Đạo, `bad` = ngày xấu/Hắc Đạo, `normal` = không nằm trong hai nhóm trên. |
| `can_chi` | `object` | Object gồm `ngay`, `thang`, `nam`; mỗi giá trị là can chi đã chuẩn hóa, tháng có thể có hậu tố `(nhuận)`. |

Các trường văn bản có thể chứa ký tự xuống dòng `\n`, dấu gạch đầu dòng hoặc dấu chấm phẩy để giữ cấu trúc diễn giải của nguồn.

## Sử dụng như API tĩnh

Bạn có thể dùng trực tiếp URL raw GitHub hoặc CDN jsDelivr. 

### Lấy dữ liệu theo năm

Raw GitHub:

```text
https://raw.githubusercontent.com/ILamTH/du-lieu-ngay-tot-xau/main/output_by_year/du_lieu_ngay_tot_xau_2025.json
```

jsDelivr:

```text
https://cdn.jsdelivr.net/gh/ILamTH/du-lieu-ngay-tot-xau@main/output_by_year/du_lieu_ngay_tot_xau_2025.json
```

### Lấy dữ liệu theo ngày

Raw GitHub:

```text
https://raw.githubusercontent.com/ILamTH/du-lieu-ngay-tot-xau/main/output_by_date/2025/01/01.json
```

jsDelivr:

```text
https://cdn.jsdelivr.net/gh/ILamTH/du-lieu-ngay-tot-xau@main/output_by_date/2025/01/01.json
```

Gợi ý lựa chọn:

- Dùng `output_by_date/` nếu ứng dụng chỉ tra cứu từng ngày riêng lẻ.
- Dùng `output_by_year/` nếu ứng dụng cần cache cả năm, hiển thị lịch tháng hoặc lọc nhiều ngày trong cùng năm.

## Ví dụ tích hợp

### JavaScript: lấy một ngày từ file năm

```js
async function getDayFromYearFile(date) {
  const year = date.slice(0, 4);
  const url = `https://cdn.jsdelivr.net/gh/ILamTH/du-lieu-ngay-tot-xau@main/output_by_year/du_lieu_ngay_tot_xau_${year}.json`;
  const data = await fetch(url).then((response) => response.json());

  return data[date] ?? null;
}

getDayFromYearFile("2025-01-01").then(console.log);
```

### JavaScript: lấy trực tiếp một ngày

```js
async function getDay(date) {
  const [year, month, day] = date.split("-");
  const url = `https://cdn.jsdelivr.net/gh/ILamTH/du-lieu-ngay-tot-xau@main/output_by_date/${year}/${month}/${day}.json`;

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Không tìm thấy dữ liệu cho ngày ${date}`);
  }

  return response.json();
}

getDay("2025-01-01").then(console.log);
```

### Python: đọc dữ liệu local theo năm

```python
import json
from pathlib import Path

with Path("output_by_year/du_lieu_ngay_tot_xau_2025.json").open(encoding="utf-8") as file:
    year_data = json.load(file)

record = year_data.get("2025-01-01")
print(record["day_quality"])
print(record["can_chi"])
```

## Nguồn dữ liệu và quy trình xử lý

Nguồn chính:

- Website: `xemlicham.com`.
- Mẫu URL ngày: `https://www.xemlicham.com/am-lich/nam/{year}/thang/{month}/ngay/{day}`.
- Mẫu URL tháng dùng khi enrich `day_quality`: `https://www.xemlicham.com/am-lich/nam/{year}/thang/{month}`.

Nguồn bổ sung khi bản ghi bị rỗng:

- Website: `lichamngay.com`.
- Mẫu URL: `https://lichamngay.com/nam-{year}/thang-{month}/lich-am-ngay-{day}-{month}-{year}.html`.

Quy trình tổng quát:

1. Crawl dữ liệu ngày từ `xemlicham.com` theo từng năm.
2. Ghi checkpoint để có thể resume nếu crawl bị gián đoạn.
3. Parse các section văn bản thành 11 trường lịch âm chính.
4. Bổ sung ngày rỗng từ `lichamngay.com` nếu cần.
5. Chuẩn hóa một số câu tiếng Việt tối nghĩa hoặc lỗi chính tả bằng bảng thay thế cố định.
6. Enrich thêm `day_quality` từ trang tháng và `can_chi` từ block header của trang ngày.
7. Tách dữ liệu theo ngày vào `output_by_date/` để dùng như API tĩnh.

Các script chỉ crawl/chuyển đổi nội dung công khai thành JSON. Nếu tái phân phối hoặc dùng trong sản phẩm thương mại, bạn nên tự kiểm tra điều khoản sử dụng, bản quyền và chính sách truy cập của website nguồn.

## Cài đặt môi trường

Yêu cầu tối thiểu:

- Python 3.10+ (do repo dùng type hint `|` trong `split_by_date.py`).
- Các thư viện Python: `requests`, `beautifulsoup4`, `tqdm`.

Cài thư viện:

```bash
python -m pip install requests beautifulsoup4 tqdm
```

Repo không có file lock dependency; nếu chạy trong môi trường production/CI, nên tự tạo virtual environment và pin phiên bản phụ thuộc theo nhu cầu.

## Các script trong repo

### `crawl_xemlicham.py`

Crawl dữ liệu từ `xemlicham.com` cho giai đoạn được cấu hình trong script.

Đặc điểm chính:

- `START_YEAR = 1901`, `END_YEAR = 2200` trong script hiện tại.
- Random thứ tự ngày trong từng năm để không request tuần tự từ đầu năm đến cuối năm.
- Có delay ngẫu nhiên, retry, timeout và user-agent tiếng Việt.
- Ghi checkpoint vào `crawl_checkpoint.jsonl` và lỗi vào `crawl_errors.jsonl`.
- Hàm output gốc của script dùng tên `lunar_calendar_xemlicham_<nam>.json`; bộ dữ liệu đã phát hành trong repo dùng tên `du_lieu_ngay_tot_xau_<nam>.json`.

Chạy:

```bash
python crawl_xemlicham.py
```

### `fill_empty_days_from_web.py`

Tìm các bản ghi rỗng trong output theo năm và bổ sung bằng `lichamngay.com`.

Chạy thử, chỉ liệt kê ngày rỗng:

```bash
python fill_empty_days_from_web.py --dry-run
```

Giới hạn số ngày cần xử lý và điều chỉnh delay:

```bash
python fill_empty_days_from_web.py --limit 100 --delay 0.2
```

Script ghi log vào `fill_empty_days_from_web.log.jsonl` với trạng thái như `fixed`, `missing_fields`, `lunar_mismatch` hoặc `error`.

### `normalize_confusing_vietnamese.py`

Duyệt toàn bộ JSON trong `output_by_year/` và thay thế các câu/cụm từ cố định bằng cách diễn đạt rõ hơn.

Chạy:

```bash
python normalize_confusing_vietnamese.py
```

Script chỉ thay nội dung chuỗi; không đổi key ngày, tên trường hay cấu trúc JSON.

Một số nhóm chuẩn hóa đáng chú ý:

| Câu/cụm gốc | Cách diễn đạt đã chuẩn hóa | Mục đích |
| --- | --- | --- |
| `Ngày này trăm sự đều kỵ không nên tiến hành bất cứ việc gì.` | `Theo quan niệm dân gian, ngày này rất kỵ; nên hạn chế tiến hành các việc quan trọng.` | Tránh tuyệt đối hóa quá mức. |
| `Phòng người người nguyền rủa, tránh lây bệnh.` | `Đề phòng điều tiếng, lời trách móc và chú ý giữ gìn sức khỏe.` | Làm rõ nghĩa, giảm sắc thái mê tín cực đoan. |
| `Giờ Tiểu Các` | `Giờ Tiểu Cát` | Sửa lỗi chữ trong ngữ cảnh giờ xuất hành. |
| `Động đất, ban nền đắp nền` | `Động thổ, san nền, đắp nền` | Sửa lỗi từ trong ngữ cảnh xây dựng/động thổ. |
| `Tránh xuất hành hướng Lên Trời gặp Hạc Thần (xấu)` | `Hạc Thần là sao xấu, nhưng ngày này Hạc Thần ở trên trời nên không xác định hướng cụ thể để tránh.` | Làm rõ `Lên Trời` không phải hướng địa lý. |

### `enrich_day_quality_can_chi.py`

Enrich thêm 2 trường:

- `day_quality`: lấy từ danh sách ngày tốt/xấu trên trang tháng.
- `can_chi`: parse từ block `div.row.header-content` của trang ngày.

Chạy test nội bộ của script:

```bash
python enrich_day_quality_can_chi.py --input-dir output_by_year --run-tests
```

Chạy thử cho một năm, không ghi file:

```bash
python enrich_day_quality_can_chi.py --input-dir output_by_year --year 2025 --dry-run
```

Cập nhật một khoảng năm:

```bash
python enrich_day_quality_can_chi.py --input-dir output_by_year --start-year 2025 --end-year 2030
```

Tùy chọn hữu ích:

- `--overwrite`: ghi đè `day_quality`/`can_chi` hiện có.
- `--sleep`: thời gian nghỉ giữa request.
- `--timeout`: timeout cho mỗi request.
- `--max-retries`: số lần retry.
- `--quiet` hoặc `--no-progress`: giảm log/progress bar.

### `split_by_date.py`

Tách file năm thành file ngày.

Tách toàn bộ dữ liệu:

```bash
python split_by_date.py --input-dir output_by_year --output-dir output_by_date
```

Tách một khoảng năm và ghi JSON compact:

```bash
python split_by_date.py --input-dir output_by_year --output-dir output_by_date --start-year 2025 --end-year 2030 --compact
```

Script kiểm tra tên file năm, key ngày `YYYY-MM-DD` và đảm bảo năm trong key khớp với năm trong tên file.

## Quy trình tái tạo/cập nhật dữ liệu

Một luồng thao tác khuyến nghị khi cần tái tạo hoặc cập nhật dữ liệu:

```bash
python crawl_xemlicham.py
python fill_empty_days_from_web.py --dry-run
python fill_empty_days_from_web.py --delay 0.2
python normalize_confusing_vietnamese.py
python enrich_day_quality_can_chi.py --input-dir output_by_year --start-year 1900 --end-year 2200
python split_by_date.py --input-dir output_by_year --output-dir output_by_date --compact
```

Sau đó nên chạy kiểm tra chất lượng JSON và thống kê số lượng bản ghi trước khi commit.

## Kiểm tra chất lượng dữ liệu

Theo kiểm tra hiện tại trong repo:

| Chỉ số | Giá trị |
| --- | ---: |
| Khoảng năm | 1900-2200 |
| Số file theo năm | 301 |
| Số file theo ngày | 109.938 |


Dù đã có kiểm tra tự động cơ bản, dữ liệu vẫn có thể còn sai sót do:

- Website nguồn thay đổi HTML, nội dung hoặc cách diễn giải.
- Lỗi mạng/timeout/redirect trong quá trình crawl.
- Parser tách section sai hoặc thiếu section khi nội dung nguồn không đồng nhất.
- Khác biệt giữa các hệ thống lịch âm, lịch vạn niên và quan niệm dân gian.
- Nội dung gốc có lỗi chính tả, lỗi dịch Hán-Việt hoặc văn phong cổ khó hiểu.

## Lưu ý sử dụng và miễn trừ trách nhiệm

Dữ liệu trong repo chỉ phục vụ mục đích tham khảo, nghiên cứu, học tập và phát triển phần mềm. Tác giả/maintainer không cam kết dữ liệu đầy đủ, chính xác tuyệt đối hoặc phù hợp với mọi mục đích sử dụng.

Thông tin ngày tốt/xấu, phong thủy, hướng xuất hành, giờ hoàng đạo/hắc đạo và các diễn giải liên quan thuộc phạm vi văn hóa, tín ngưỡng và kinh nghiệm dân gian. Không nên xem dữ liệu này là cơ sở duy nhất để đưa ra quyết định quan trọng về pháp lý, tài chính, y tế, hôn nhân, xây dựng, kinh doanh hoặc các vấn đề có rủi ro cao.

Người sử dụng tự chịu trách nhiệm khi áp dụng, phân phối lại hoặc tích hợp dữ liệu vào sản phẩm khác.

## Đóng góp

Nếu phát hiện sai sót, vui lòng tạo issue hoặc pull request kèm thông tin cụ thể:

- Ngày dương lịch bị lỗi, ví dụ `2025-01-01`.
- File liên quan, ví dụ `output_by_year/du_lieu_ngay_tot_xau_2025.json` hoặc `output_by_date/2025/01/01.json`.
- Trường bị lỗi, nội dung hiện tại và nội dung đề xuất.
- Nguồn tham chiếu nếu có.
