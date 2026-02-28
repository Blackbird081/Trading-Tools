---
name: "risk_assessment"
description: "Đánh giá rủi ro toàn diện: VaR, position sizing, stop-loss, kill switch"
---

# Quy Trình Đánh Giá Rủi Ro

## Bước 1: Kill Switch Check
- Kiểm tra kill_switch_active trước tiên
- Nếu active: DỪNG NGAY, không phân tích tiếp

## Bước 2: Price Band Validation
- HOSE: ±7% từ giá tham chiếu
- HNX: ±10%
- UPCOM: ±15%
- Lệnh phải nằm trong band

## Bước 3: Lot Size Check
- Số lượng phải là bội số của 100
- Ví dụ: 100, 200, 500, 1000 ✓
- 150, 250 ✗

## Bước 4: Position Size Limit
- Tính giá trị lệnh = giá × số lượng
- Tính % NAV = giá trị lệnh / NAV
- Giới hạn: ≤ 20% NAV mỗi lệnh
- Nếu vượt: từ chối lệnh

## Bước 5: Buying Power (BUY orders)
- Kiểm tra purchasing_power ≥ giá trị lệnh
- Nếu không đủ: từ chối lệnh

## Bước 6: Sellable Quantity (SELL orders)
- Kiểm tra sellable_qty ≥ số lượng muốn bán
- Lưu ý T+2.5: chỉ cổ phiếu đã settled mới bán được
- Trừ pending_sell_qty nếu có lệnh bán đang chờ

## Bước 7: Daily Loss Limit
- Kiểm tra daily_pnl < -max_daily_loss
- Nếu vượt: DỪNG giao dịch hôm nay

## Bước 8: VaR Calculation
- Historical VaR 95% với 252 ngày dữ liệu
- Nếu VaR > 5% NAV: cảnh báo rủi ro cao

## Bước 9: Stop-Loss & Take-Profit
- Stop-loss: -7% từ giá vào (tương đương giá sàn HOSE)
- Take-profit: +10% từ giá vào
- Trailing stop: 5% từ đỉnh

## Kết Luận
Tổng hợp tất cả checks:
- Tất cả pass: APPROVED
- Bất kỳ fail: REJECTED + lý do cụ thể
