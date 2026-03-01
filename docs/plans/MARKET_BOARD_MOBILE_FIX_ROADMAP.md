# Market Board Mobile Fix Roadmap

## Scope
- Chi sua tab `Bảng điện` (`/market-board`).
- Khong thay doi cac tab khac.
- Muc tieu: mobile de doc, de cuon, khong bi day nhieu cot kho nhin.
- Non-regression bat buoc: click vao ma co phieu van mo popup chi tiet nhu hien tai.

## Current Issues
- Mobile dang render tat ca sector trong 1 trang, nhieu block lien tiep nen mat do thong tin qua day.
- Luong dieu huong page (Trang 1/Trang 2) chi co tren desktop, mobile khong co nen kho xem theo nhom.
- Sector card mobile dang toi uu cho desktop-style row density, chua toi uu cho cach xem nhanh theo trang.

## Target UX
- Mobile: chi hien thi 1 sector tai 1 thoi diem (VD: VN30 hoac Bat dong san...).
- Mobile: co dieu huong sector ro rang (tab + nut Truoc/Tiep).
- Mobile: neu so ma nhieu, co thao tac cuon them de xem het.
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

### Phase 3 - Mobile Single-Sector Screen
- Chuyen mobile tu "3 sector/page" sang "1 sector/man hinh".
- Them dieu huong sector bang tab ngang va nut Truoc/Tiep.
- Moi lan chi render 1 `SectorColumn` tren mobile de toi da khong gian doc.
- Dam bao click ma van mo popup chi tiet (khong thay doi hanh vi nay).

### Phase 4 - Scroll More for Long Sector Lists
- Neu so ma trong sector nhieu, them thao tac "Cuon them" de nhay xuong phan tiep theo.
- Giu cuon doc tu nhien va khong anh huong desktop.

### Phase 5 - QA + Stability
- Test viewport iPhone: 390x844, 393x852, 430x932.
- Check khong con tinh trang kho doc do qua nhieu block trong cung man hinh.
- Run `lint`, `type-check`, `test` frontend.

## Acceptance Criteria
- Mobile chi hien thi 1 sector tai 1 thoi diem.
- Co the doi sector nhanh tren mobile (tab + Truoc/Tiep).
- Co thao tac cuon them khi danh sach ma dai.
- Click vao ma co phieu tren mobile van mo popup chi tiet nhu truoc.
- Desktop khong bi hoi quy (van 3 cot/page + footer pagination).

## Files Expected
- `frontend/app/market-board/page.tsx`
- (Phase 2 co the them) `frontend/components/sector-column.tsx`
