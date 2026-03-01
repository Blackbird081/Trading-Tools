# Market Board Mobile Fix Roadmap

## Scope
- Chi sua tab `Bảng điện` (`/market-board`).
- Khong thay doi cac tab khac.
- Muc tieu: mobile de doc, de cuon, khong bi day nhieu cot kho nhin.

## Current Issues
- Mobile dang render tat ca sector trong 1 trang, nhieu block lien tiep nen mat do thong tin qua day.
- Luong dieu huong page (Trang 1/Trang 2) chi co tren desktop, mobile khong co nen kho xem theo nhom.
- Sector card mobile dang toi uu cho desktop-style row density, chua toi uu cho cach xem nhanh theo trang.

## Target UX
- Mobile: chi hien thi 1 page tai 1 thoi diem, moi page gom 3 sector.
- Mobile: cuon doc trong page do, co dieu huong Trang 1/Trang 2 ro rang.
- Desktop: giu nguyen hien trang 3 cot + pagination footer.

## Phase Plan

### Phase 1 - Mobile One-Page Mode (implement first)
- Doi mobile tu render `SECTORS` thanh render `pageSectors` (3 sector/page).
- Tai su dung `currentPage` da co de desktop/mobile dong bo logic.
- Them thanh dieu huong trang cho mobile (Trang 1/Trang 2 + nut Truoc/Tiep gon).
- Khong thay doi style sau cua tung row o phase nay.

### Phase 2 - Mobile Readability Tuning
- Tinh chinh spacing mobile trong `SectorColumn` (padding, row height, text size).
- Tang do ro cot `Mã | Giá | % | KL`, dam bao khong cat chu tren iPhone.
- Giu desktop style khong doi.

### Phase 3 - QA + Stability
- Test viewport iPhone: 390x844, 393x852, 430x932.
- Check khong con tinh trang kho doc do qua nhieu block trong cung man hinh.
- Run `lint`, `type-check`, `test` frontend.

## Acceptance Criteria
- Mobile chi hien thi 1 page sector tai 1 thoi diem.
- Co the chuyen page nhanh tren mobile, cuon doc de xem het noi dung page.
- Desktop khong bi hoi quy (van 3 cot/page + footer pagination).

## Files Expected
- `frontend/app/market-board/page.tsx`
- (Phase 2 co the them) `frontend/components/sector-column.tsx`
