import type { TickData } from "@/types/market";

export type MarketPreset = "VN30" | "TOP100";

export interface MarketSector {
  title: string;
  symbols: string[];
}

export const VN30_SYMBOLS: string[] = [
  "ACB",
  "BCM",
  "BID",
  "BVH",
  "CTG",
  "FPT",
  "GAS",
  "GVR",
  "HDB",
  "HPG",
  "MBB",
  "MSN",
  "MWG",
  "PLX",
  "POW",
  "SAB",
  "SHB",
  "SSB",
  "SSI",
  "STB",
  "TCB",
  "TPB",
  "VCB",
  "VHM",
  "VIB",
  "VIC",
  "VJC",
  "VNM",
  "VPB",
  "VRE",
];

export const TOP100_SYMBOLS: string[] = [
  ...VN30_SYMBOLS,
  "AAA",
  "ANV",
  "ASM",
  "BSI",
  "BWE",
  "CII",
  "CMG",
  "DBC",
  "DCM",
  "DGC",
  "DIG",
  "DPM",
  "DXG",
  "EIB",
  "EVF",
  "FCN",
  "GEX",
  "GMD",
  "HAG",
  "HCM",
  "HDC",
  "HDG",
  "HNG",
  "HSG",
  "HT1",
  "IMP",
  "KBC",
  "KDC",
  "KDH",
  "KOS",
  "LPB",
  "MSB",
  "NLG",
  "NT2",
  "NVL",
  "OCB",
  "PC1",
  "PDR",
  "PET",
  "PHR",
  "PNJ",
  "PPC",
  "PVD",
  "PVS",
  "PVT",
  "REE",
  "SBT",
  "SCS",
  "SIP",
  "SJS",
  "SSB",
  "SZC",
  "TCH",
  "TLG",
  "TNH",
  "VCI",
  "VGC",
  "VHC",
  "VIX",
  "VND",
  "VOS",
  "VPI",
  "VTP",
  "HAH",
  "DGW",
  "FRT",
  "LHG",
  "CTR",
  "VTO",
  "AGG",
];

const CATEGORY_ORDER = [
  "Bất động sản",
  "Chứng khoán",
  "Ngân hàng",
  "Thép",
  "Dầu khí",
  "Tiện ích",
  "Công nghệ",
  "Bán lẻ",
  "Vận tải",
  "Nông nghiệp",
  "Công nghiệp",
  "Khác",
] as const;

const SYMBOL_CATEGORY: Record<string, (typeof CATEGORY_ORDER)[number]> = {
  AGG: "Bất động sản",
  DIG: "Bất động sản",
  DXG: "Bất động sản",
  HDC: "Bất động sản",
  HDG: "Bất động sản",
  KBC: "Bất động sản",
  KDH: "Bất động sản",
  KOS: "Bất động sản",
  NLG: "Bất động sản",
  NVL: "Bất động sản",
  PDR: "Bất động sản",
  SIP: "Bất động sản",
  SJS: "Bất động sản",
  SZC: "Bất động sản",
  TCH: "Bất động sản",
  VHM: "Bất động sản",
  VIC: "Bất động sản",
  VPI: "Bất động sản",
  VRE: "Bất động sản",
  BSI: "Chứng khoán",
  HCM: "Chứng khoán",
  SSI: "Chứng khoán",
  VCI: "Chứng khoán",
  VIX: "Chứng khoán",
  VND: "Chứng khoán",
  ACB: "Ngân hàng",
  BID: "Ngân hàng",
  CTG: "Ngân hàng",
  EIB: "Ngân hàng",
  HDB: "Ngân hàng",
  LPB: "Ngân hàng",
  MBB: "Ngân hàng",
  MSB: "Ngân hàng",
  OCB: "Ngân hàng",
  SHB: "Ngân hàng",
  SSB: "Ngân hàng",
  STB: "Ngân hàng",
  TCB: "Ngân hàng",
  TPB: "Ngân hàng",
  VCB: "Ngân hàng",
  VIB: "Ngân hàng",
  VPB: "Ngân hàng",
  HPG: "Thép",
  HSG: "Thép",
  HT1: "Thép",
  BSR: "Dầu khí",
  GAS: "Dầu khí",
  PLX: "Dầu khí",
  PVD: "Dầu khí",
  PVS: "Dầu khí",
  PVT: "Dầu khí",
  BWE: "Tiện ích",
  NT2: "Tiện ích",
  PC1: "Tiện ích",
  POW: "Tiện ích",
  PPC: "Tiện ích",
  REE: "Tiện ích",
  CMG: "Công nghệ",
  CTR: "Công nghệ",
  FPT: "Công nghệ",
  VTP: "Công nghệ",
  DGW: "Bán lẻ",
  FRT: "Bán lẻ",
  KDC: "Bán lẻ",
  MWG: "Bán lẻ",
  PNJ: "Bán lẻ",
  SAB: "Bán lẻ",
  VNM: "Bán lẻ",
  GMD: "Vận tải",
  HAH: "Vận tải",
  SCS: "Vận tải",
  VOS: "Vận tải",
  VTO: "Vận tải",
  ANV: "Nông nghiệp",
  ASM: "Nông nghiệp",
  DBC: "Nông nghiệp",
  HAG: "Nông nghiệp",
  HNG: "Nông nghiệp",
  SBT: "Nông nghiệp",
  VHC: "Nông nghiệp",
  AAA: "Công nghiệp",
  BCM: "Công nghiệp",
  BVH: "Công nghiệp",
  CII: "Công nghiệp",
  DCM: "Công nghiệp",
  DGC: "Công nghiệp",
  DPM: "Công nghiệp",
  EVF: "Công nghiệp",
  FCN: "Công nghiệp",
  GEX: "Công nghiệp",
  GVR: "Công nghiệp",
  IMP: "Công nghiệp",
  LHG: "Công nghiệp",
  MSN: "Công nghiệp",
  PET: "Công nghiệp",
  PHR: "Công nghiệp",
  TLG: "Công nghiệp",
  TNH: "Công nghiệp",
  VGC: "Công nghiệp",
  VJC: "Công nghiệp",
};

export function buildMarketSectors(
  preset: MarketPreset,
  ticks: Record<string, TickData>,
): MarketSector[] {
  const universe = [...new Set(preset === "VN30" ? VN30_SYMBOLS : TOP100_SYMBOLS)];
  const universeSet = new Set(universe);
  const activeTickSymbols = Object.keys(ticks).filter((symbol) => universeSet.has(symbol));
  const sourceSet = new Set(activeTickSymbols.length > 0 ? activeTickSymbols : universe);
  const orderedSymbols = universe.filter((symbol) => sourceSet.has(symbol));

  if (preset === "VN30") {
    return [{ title: "VN30", symbols: orderedSymbols }];
  }

  const vn30Set = new Set(VN30_SYMBOLS);
  const sectorBuckets = new Map<string, string[]>();
  for (const title of CATEGORY_ORDER) {
    sectorBuckets.set(title, []);
  }

  const vn30Symbols = orderedSymbols.filter((symbol) => vn30Set.has(symbol));
  const nonVn30Symbols = orderedSymbols.filter((symbol) => !vn30Set.has(symbol));

  for (const symbol of nonVn30Symbols) {
    const title = SYMBOL_CATEGORY[symbol] ?? "Khác";
    const bucket = sectorBuckets.get(title) ?? [];
    bucket.push(symbol);
    sectorBuckets.set(title, bucket);
  }

  const sectors: MarketSector[] = [];
  if (vn30Symbols.length > 0) {
    sectors.push({ title: "VN30", symbols: vn30Symbols });
  }

  for (const title of CATEGORY_ORDER) {
    const symbols = sectorBuckets.get(title) ?? [];
    if (symbols.length > 0) {
      sectors.push({ title, symbols });
    }
  }

  if (sectors.length > 0) {
    return sectors;
  }

  return [{ title: "Top 100", symbols: orderedSymbols }];
}
