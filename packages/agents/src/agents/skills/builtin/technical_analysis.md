---
name: "technical_analysis"
description: "Phân tích kỹ thuật toàn diện: RSI, MACD, Bollinger Bands, MA50/200, Volume"
---

# Quy Trình Phân Tích Kỹ Thuật

Khi được yêu cầu phân tích kỹ thuật một cổ phiếu, hãy thực hiện theo thứ tự sau:

## Bước 1: Thu Thập Dữ Liệu
- Lấy dữ liệu OHLCV ít nhất 200 phiên gần nhất
- Kiểm tra khối lượng giao dịch trung bình 20 phiên

## Bước 2: Phân Tích Xu Hướng
- **MA50 vs MA200**: Golden cross (MA50 > MA200) = xu hướng tăng dài hạn
- **Giá vs MA20**: Giá trên MA20 = xu hướng ngắn hạn tích cực
- **Kênh giá**: Xác định support/resistance quan trọng

## Bước 3: Momentum Indicators
- **RSI (14)**: 
  - < 30: Oversold → tín hiệu mua tiềm năng
  - > 70: Overbought → tín hiệu bán tiềm năng
  - 30-70: Trung tính
- **MACD (12,26,9)**:
  - Bullish cross (MACD > Signal): tín hiệu mua
  - Bearish cross (MACD < Signal): tín hiệu bán
  - Histogram dương/âm: xác nhận momentum

## Bước 4: Volatility
- **Bollinger Bands (20,2)**:
  - Giá tại lower band: oversold, có thể bounce
  - Giá tại upper band: overbought, có thể pullback
  - Band squeeze: chuẩn bị breakout

## Bước 5: Volume Confirmation
- Volume spike (> 2x trung bình): xác nhận tín hiệu
- Volume thấp khi giá tăng: tín hiệu yếu, cần thận trọng

## Bước 6: Tổng Hợp Điểm Số
Tính composite score (-10 đến +10):
- RSI oversold: +3, RSI overbought: -3
- MACD bullish cross: +3, bearish cross: -3
- BB below lower: +2, above upper: -2
- Golden cross: +2, Death cross: -2

## Kết Luận
- Score ≥ 5: BUY
- Score ≤ -5: SELL
- -5 < Score < 5: NEUTRAL

**Lưu ý thị trường VN**: Giá trần/sàn ±7% (HOSE) có thể giới hạn momentum. Kiểm tra xem giá có đang tiếp cận trần/sàn không.
