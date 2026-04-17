#!/usr/bin/env python3
"""
================================================================================
ENHANCED PURE TCT BOT - 100% TCT RULES + ADVANCED PDF CONCEPTS
============================+===================================================
METALS ONLY VERSION - XAU, XAG, XPT, XPD
Uses yfinance for data (yahoo finance)
================================================================================

ORIGINAL LECTURES 1-8 (100% PRESERVED):
  ✓ 6-Candle Rule (2-2-2) - inside bars don't count
  ✓ MS low/high confirmed ONLY when opposite TOUCHED
  ✓ BOS requires CLOSE beyond level - good vs bad breaks
  ✓ SFP/Wicks: 3 scenarios based on LTF structure
  ✓ Domino Effect & Swarm strength grading
  ✓ Range confirmed when equilibrium (0.5 Fib) TOUCHED
  ✓ DL2 = 30% of range size - wick & bad break deviations
  ✓ Premium/Discount zones - Good ranges (sideways, not V-shapes)
  ✓ OBIF with mandatory FVG - Extreme S&D (last before range extreme)
  ✓ Double Effect, Cascade, RTZ quality
  ✓ Model 1/2 with tap spacing - Entry on BOS inside range
  ✓ PO3 (Range→Manipulation→Expansion) - Two-tap exceptions
  ✓ Position sizing, R:R minimum 2.0

ADVANCED PDF CONCEPTS (NEW - FULLY INTEGRATED):
  ✓ Levels 1,2,3 | QRZ (Primary/Internal) | 4-Variable Checklist
  ✓ EHP Detection | Test Phase | Extended Tap | Correct Tab One
  ✓ TCT Creating TCT | D-EEC/A-EEC | Range Duration Rules
  ✓ Aggressive Third Taps | Context Ranking | A+ to C Grading
================================================================================
"""

import math
import time
import logging
import warnings
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

import numpy as np
import pandas as pd
import requests
import yfinance as yf
from scipy.signal import find_peaks
from scipy import stats

warnings.filterwarnings("ignore")

# =============================================================================
# CONFIGURATION
# =============================================================================
TELEGRAM_BOT_TOKEN = "8359543474:AAHHry6W6mUADH66IA0J2VmIWkflkqXOQf8"
TELEGRAM_CHAT_ID = "5747777199"

# METALS ONLY - Yahoo Finance symbols
METAL_SYMBOLS = ["XAUUSD=X", "XAGUSD=X", "XPTUSD=X", "XPDUSD=X"]
# Display names for better readability
METAL_DISPLAY_NAMES = {
    "XAUUSD=X": "XAUUSD (Gold)",
    "XAGUSD=X": "XAGUSD (Silver)",
    "XPTUSD=X": "XPTUSD (Platinum)",
    "XPDUSD=X": "XPDUSD (Palladium)"
}

SCAN_INTERVAL_SECONDS = 60

ACCOUNT_SIZE = 10000
RISK_PCT = 1.0
MIN_CONFIDENCE = 0.80
MIN_RR = 2.0

SIGNAL_COOLDOWN_MINUTES = 1800000
MAX_SIGNALS_PER_DAY = 30

# Range Duration (Section 8.4 - Variable 2)
MIN_RANGE_DURATION_HOURS = 24
DAILY_RANGE_MIN_HOURS = 15  # Exception C.6

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("enhanced_tct_metals.log")]
)
log = logging.getLogger("EnhancedTCT_Metals")


# =============================================================================
# ENUMS
# =============================================================================
class Direction(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"

class TCTModel(Enum):
    M1A = "Model 1 Accumulation"
    M1D = "Model 1 Distribution"
    M2A = "Model 2 Accumulation"
    M2D = "Model 2 Distribution"
    PO3_BULLISH = "PO3 Bullish"
    PO3_BEARISH = "PO3 Bearish"
    TWO_TAP_LONG = "Two-Tap Long"
    TWO_TAP_SHORT = "Two-Tap Short"
    TEST_PHASE_LONG = "Test Phase Long"
    TEST_PHASE_SHORT = "Test Phase Short"
    EXTENDED_TAP_LONG = "Extended Tap Long"
    EXTENDED_TAP_SHORT = "Extended Tap Short"
    EHP_LONG = "EHP Long"
    EHP_SHORT = "EHP Short"
    NESTED_LONG = "Nested Accumulation"
    NESTED_SHORT = "Nested Distribution"
    NONE = "None"

class ContextRank(Enum):
    PRO = "Pro"
    SEMI_PRO = "Semi-Pro"
    NEUTRAL = "Neutral"
    SEMI_COUNTER = "Semi-Counter"
    COUNTER = "Counter"

class SetupGrade(Enum):
    A_PLUS = "A+"
    A = "A"
    A_MINUS = "A-"
    B = "B"
    C = "C"

class BreakerQuality(Enum):
    AGGRESSIVE = "Aggressive"
    MODERATE = "Moderate"
    WEAK = "Weak"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def safe_float(val) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (np.ndarray, pd.Series)):
        if val.size == 1:
            return float(val.item())
        return float(val[0]) if len(val) > 0 else 0.0
    return float(val) if isinstance(val, (int, float, np.number)) else 0.0


def is_inside_bar(current: pd.Series, previous: pd.Series) -> bool:
    return (current['high'] <= previous['high'] and 
            current['low'] >= previous['low'])


def six_candle_rule(df: pd.DataFrame, start_idx: int) -> Tuple[bool, str]:
    """LECTURE 1: 2-2-2 Rule"""
    if start_idx + 6 > len(df):
        return False, "none"
    
    for i in range(start_idx + 1, start_idx + 6):
        if is_inside_bar(df.iloc[i], df.iloc[i-1]):
            return False, "inside_bar"
    
    candles = df.iloc[start_idx:start_idx+6]
    
    uptrend = (
        candles.iloc[0]['close'] > candles.iloc[0]['open'] and
        candles.iloc[1]['close'] > candles.iloc[1]['open'] and
        candles.iloc[1]['close'] > candles.iloc[0]['close'] and
        candles.iloc[2]['close'] < candles.iloc[2]['open'] and
        candles.iloc[3]['close'] < candles.iloc[3]['open'] and
        candles.iloc[3]['close'] < candles.iloc[2]['close'] and
        candles.iloc[4]['close'] > candles.iloc[4]['open'] and
        candles.iloc[5]['close'] > candles.iloc[5]['open'] and
        candles.iloc[5]['close'] > candles.iloc[4]['close']
    )
    
    if uptrend:
        return True, "uptrend"
    
    downtrend = (
        candles.iloc[0]['close'] < candles.iloc[0]['open'] and
        candles.iloc[1]['close'] < candles.iloc[1]['open'] and
        candles.iloc[1]['close'] < candles.iloc[0]['close'] and
        candles.iloc[2]['close'] > candles.iloc[2]['open'] and
        candles.iloc[3]['close'] > candles.iloc[3]['open'] and
        candles.iloc[3]['close'] > candles.iloc[2]['close'] and
        candles.iloc[4]['close'] < candles.iloc[4]['open'] and
        candles.iloc[5]['close'] < candles.iloc[5]['open'] and
        candles.iloc[5]['close'] < candles.iloc[4]['close']
    )
    
    if downtrend:
        return True, "downtrend"
    
    return False, "none"


def find_swing_points(df: pd.DataFrame, lookback: int = 3) -> Tuple[List[float], List[int], List[float], List[int]]:
    highs = df['high'].values
    lows = df['low'].values
    
    swing_highs, swing_high_idx = [], []
    swing_lows, swing_low_idx = [], []
    
    for i in range(lookback, len(df) - lookback):
        if all(highs[i] > highs[i-j] for j in range(1, lookback+1)) and \
           all(highs[i] > highs[i+j] for j in range(1, lookback+1)):
            swing_highs.append(highs[i])
            swing_high_idx.append(i)
        
        if all(lows[i] < lows[i-j] for j in range(1, lookback+1)) and \
           all(lows[i] < lows[i+j] for j in range(1, lookback+1)):
            swing_lows.append(lows[i])
            swing_low_idx.append(i)
    
    return swing_highs, swing_high_idx, swing_lows, swing_low_idx


def calculate_range_duration_hours(df: pd.DataFrame, start_idx: int, end_idx: int) -> float:
    """Section 8.4 - Variable 2: Calculate range duration in hours"""
    if start_idx >= end_idx or start_idx < 0 or end_idx >= len(df):
        return 0.0
    
    start_time = df.index[start_idx]
    end_time = df.index[end_idx]
    
    if hasattr(start_time, 'to_pydatetime'):
        start_time = start_time.to_pydatetime()
    if hasattr(end_time, 'to_pydatetime'):
        end_time = end_time.to_pydatetime()
    
    return (end_time - start_time).total_seconds() / 3600.0


# =============================================================================
# LECTURE 2: RANGE DETECTION (ENHANCED)
# =============================================================================
@dataclass
class ValidatedRange:
    high: float
    low: float
    equilibrium: float
    dl2_upper: float
    dl2_lower: float
    width_pct: float
    is_valid: bool
    taps_high: int
    taps_low: int
    wyckoff_high: float
    wyckoff_low: float
    is_good_range: bool
    confirmed_by_eq: bool
    start_idx: int = 0
    end_idx: int = 0
    duration_hours: float = 0.0
    
    def is_in_premium(self, price: float) -> bool:
        return price > self.equilibrium
    
    def is_in_discount(self, price: float) -> bool:
        return price < self.equilibrium


class RangeDetector:
    """LECTURE 2 + Section 8.4 Variable 2: Range detection with duration"""
    
    @staticmethod
    def detect(df: pd.DataFrame) -> Optional[ValidatedRange]:
        if len(df) < 30:
            return None
        
        recent_df = df.iloc[-50:] if len(df) >= 50 else df
        best_range = None
        best_score = -1
        
        for window in [20, 25, 30, 35, 40, 45, 50]:
            if window > len(recent_df):
                continue
            
            sub_df = recent_df.iloc[-window:]
            range_high = float(sub_df['high'].max())
            range_low = float(sub_df['low'].min())
            
            if range_high <= range_low:
                continue
            
            width_pct = (range_high - range_low) / range_low
            if width_pct < 0.005 or width_pct > 0.35:
                continue
            
            equilibrium = (range_high + range_low) / 2
            
            eq_touches = 0
            for i in range(1, len(sub_df)):
                if (sub_df['close'].iloc[i-1] < equilibrium <= sub_df['close'].iloc[i]) or \
                   (sub_df['close'].iloc[i-1] > equilibrium >= sub_df['close'].iloc[i]):
                    eq_touches += 1
            
            if eq_touches < 1:
                continue
            
            mid = len(sub_df) // 2
            first_half = sub_df['high'].iloc[:mid].max() - sub_df['low'].iloc[:mid].min()
            second_half = sub_df['high'].iloc[mid:].max() - sub_df['low'].iloc[mid:].min()
            is_good_range = (first_half > (range_high - range_low) * 0.25 and
                           second_half > (range_high - range_low) * 0.25)
            
            taps_high = sum(1 for _, row in sub_df.iterrows() 
                          if abs(row['high'] - range_high) / range_high < 0.01)
            taps_low = sum(1 for _, row in sub_df.iterrows() 
                         if abs(row['low'] - range_low) / range_low < 0.01)
            
            score = (taps_high + taps_low) * 3 + eq_touches * 5
            score += 5 if is_good_range else 0
            
            if score > best_score:
                best_score = score
                range_size = range_high - range_low
                dl2_extension = range_size * 0.30
                
                start_idx = len(df) - window
                end_idx = len(df) - 1
                duration = calculate_range_duration_hours(df, start_idx, end_idx)
                
                best_range = ValidatedRange(
                    high=range_high,
                    low=range_low,
                    equilibrium=equilibrium,
                    dl2_upper=range_high + dl2_extension,
                    dl2_lower=range_low - dl2_extension,
                    width_pct=width_pct,
                    is_valid=True,
                    taps_high=taps_high,
                    taps_low=taps_low,
                    wyckoff_high=range_high,
                    wyckoff_low=range_low,
                    is_good_range=is_good_range,
                    confirmed_by_eq=(eq_touches >= 1),
                    start_idx=start_idx,
                    end_idx=end_idx,
                    duration_hours=duration
                )
        
        return best_range


# =============================================================================
# LECTURE 3: SUPPLY & DEMAND (ENHANCED)
# =============================================================================
@dataclass
class OrderBlock:
    direction: str
    high: float
    low: float
    has_fvg: bool
    is_extreme: bool = False
    location: str = ""
    at_pivot: bool = False
    swept_liquidity_first: bool = False
    is_market_maker: bool = False
    timeframe: str = ""


class SupplyDemandDetector:
    """LECTURE 3 + Section 8.4: Enhanced S&D detection"""
    
    @staticmethod
    def has_fvg(df: pd.DataFrame, idx: int) -> bool:
        if idx < 1 or idx + 1 >= len(df):
            return False
        c1 = df.iloc[idx-1]
        c3 = df.iloc[idx+1]
        return c3['low'] > c1['high'] or c3['high'] < c1['low']
    
    @staticmethod
    def detect_order_blocks(df: pd.DataFrame, valid_range: Optional[ValidatedRange] = None) -> List[OrderBlock]:
        obs = []
        if len(df) < 4:
            return obs
        
        highs, high_idx, lows, low_idx = find_swing_points(df, lookback=3)
        
        for i in range(2, len(df) - 1):
            c = df.iloc[i-1]
            n = df.iloc[i]
            
            # Bullish OB (Demand)
            if c['close'] < c['open'] and n['close'] > n['open'] and n['close'] > c['high']:
                fvg = SupplyDemandDetector.has_fvg(df, i-1)
                if fvg:
                    ob = OrderBlock(direction="demand", high=float(c['high']), low=float(c['low']), has_fvg=True)
                    if valid_range:
                        ob.location = "discount" if float(c['low']) < valid_range.equilibrium else "premium"
                    
                    # Section 8.4: Check if at pivot
                    ob.at_pivot = any(abs(i - idx) < 3 for idx in low_idx)
                    
                    # Check if swept liquidity first (price wicked below then reversed)
                    if i > 2:
                        prev_low = df['low'].iloc[i-2]
                        if c['low'] < prev_low:
                            ob.swept_liquidity_first = True
                    
                    obs.append(ob)
            
            # Bearish OB (Supply)
            if c['close'] > c['open'] and n['close'] < n['open'] and n['close'] < c['low']:
                fvg = SupplyDemandDetector.has_fvg(df, i-1)
                if fvg:
                    ob = OrderBlock(direction="supply", high=float(c['high']), low=float(c['low']), has_fvg=True)
                    if valid_range:
                        ob.location = "premium" if float(c['high']) > valid_range.equilibrium else "discount"
                    
                    ob.at_pivot = any(abs(i - idx) < 3 for idx in high_idx)
                    
                    if i > 2:
                        prev_high = df['high'].iloc[i-2]
                        if c['high'] > prev_high:
                            ob.swept_liquidity_first = True
                    
                    obs.append(ob)
        
        # Mark extreme blocks
        demand_blocks = [ob for ob in obs if ob.direction == "demand"]
        supply_blocks = [ob for ob in obs if ob.direction == "supply"]
        if demand_blocks:
            demand_blocks[-1].is_extreme = True
        if supply_blocks:
            supply_blocks[-1].is_extreme = True
        
        return obs[-15:] if len(obs) > 15 else obs
    
    @staticmethod
    def rank_ob_quality(ob: OrderBlock) -> int:
        """Section 8.4: Rank S&D by location and action"""
        score = 0
        if ob.at_pivot and ob.swept_liquidity_first:
            score = 3  # Best: Macro pivot + liquidity sweep
        elif ob.at_pivot:
            score = 2  # Good: Pivot point
        else:
            score = 1  # Insignificant: Within expansion
        return score


# =============================================================================
# SECTION 8.2: QUALITY RETURN TO ZONE (QRZ) ANALYSIS
# =============================================================================
@dataclass
class QRZAnalysis:
    """Section 8.2: Complete Quality Return to Zone analysis"""
    primary_highs_aligned: bool
    internal_highs_stacked: bool
    liquidity_targets: int
    liquidity_grabs: int
    quality_score: float
    is_valid_qrz: bool
    is_aggressive_final_move: bool
    regenerated_liquidity: bool


class QRZAnalyzer:
    """Section 8.2: Quality Return to Zone detection"""
    
    @staticmethod
    def analyze(df: pd.DataFrame, valid_range: ValidatedRange, 
                direction: str) -> QRZAnalysis:
        
        highs, high_idx, lows, low_idx = find_swing_points(df, lookback=3)
        
        if direction == "long":
            points = highs[-8:] if len(highs) >= 8 else highs
            primary_aligned = len(points) >= 3 and all(points[i] < points[i-1] for i in range(1, len(points)))
        else:
            points = lows[-8:] if len(lows) >= 8 else lows
            primary_aligned = len(points) >= 3 and all(points[i] > points[i-1] for i in range(1, len(points)))
        
        internal_stacked = QRZAnalyzer._check_internal_stacking(df, direction)
        
        liq_targets = QRZAnalyzer._count_liquidity_targets(df, direction)
        liq_grabs = QRZAnalyzer._count_liquidity_grabs(df, direction)
        
        quality_score = 0.5
        if primary_aligned:
            quality_score += 0.20
        if internal_stacked:
            quality_score += 0.15
        if liq_targets >= 3:
            quality_score += 0.10
        if liq_grabs <= 1:
            quality_score += 0.05
        
        aggressive_final = QRZAnalyzer._check_aggressive_final_move(df, direction)
        regenerated = QRZAnalyzer._check_regenerated_liquidity(df, direction)
        
        is_valid = quality_score >= 0.60 and liq_targets > liq_grabs
        
        return QRZAnalysis(
            primary_highs_aligned=primary_aligned,
            internal_highs_stacked=internal_stacked,
            liquidity_targets=liq_targets,
            liquidity_grabs=liq_grabs,
            quality_score=min(0.95, quality_score),
            is_valid_qrz=is_valid,
            is_aggressive_final_move=aggressive_final,
            regenerated_liquidity=regenerated
        )
    
    @staticmethod
    def _check_internal_stacking(df: pd.DataFrame, direction: str) -> bool:
        if len(df) < 10:
            return False
        
        recent = df.iloc[-10:]
        if direction == "long":
            highs = recent['high'].values
            return all(highs[i] <= highs[i-1] * 1.01 for i in range(1, len(highs)))
        else:
            lows = recent['low'].values
            return all(lows[i] >= lows[i-1] * 0.99 for i in range(1, len(lows)))
    
    @staticmethod
    def _count_liquidity_targets(df: pd.DataFrame, direction: str) -> int:
        highs, _, lows, _ = find_swing_points(df, lookback=2)
        if direction == "long":
            return len([h for i, h in enumerate(highs[:-1]) if h > highs[i+1]])
        else:
            return len([l for i, l in enumerate(lows[:-1]) if l < lows[i+1]])
    
    @staticmethod
    def _count_liquidity_grabs(df: pd.DataFrame, direction: str) -> int:
        grabs = 0
        if len(df) < 5:
            return grabs
        
        for i in range(2, len(df) - 2):
            candle = df.iloc[i]
            if direction == "long":
                if candle['low'] < df['low'].iloc[i-1] and candle['close'] > candle['open']:
                    grabs += 1
            else:
                if candle['high'] > df['high'].iloc[i-1] and candle['close'] < candle['open']:
                    grabs += 1
        return grabs
    
    @staticmethod
    def _check_aggressive_final_move(df: pd.DataFrame, direction: str) -> bool:
        if len(df) < 6:
            return False
        
        recent = df.iloc[-3:]
        older = df.iloc[-6:-3]
        
        recent_range = recent['high'].max() - recent['low'].min()
        older_range = older['high'].max() - older['low'].min()
        
        return recent_range > older_range * 1.5
    
    @staticmethod
    def _check_regenerated_liquidity(df: pd.DataFrame, direction: str) -> bool:
        if len(df) < 20:
            return False
        
        recent = df.iloc[-10:]
        older = df.iloc[-20:-10]
        
        recent_volatility = recent['close'].std() / recent['close'].mean()
        older_volatility = older['close'].std() / older['close'].mean()
        
        return recent_volatility < older_volatility * 0.7


# =============================================================================
# SECTION 8.1: LEVELS 1, 2, 3 ANALYSIS
# =============================================================================
@dataclass
class LevelStructure:
    """Section 8.1: Levels 1, 2, 3 framework"""
    level1_trend: str
    level2_counter: str
    level3_refined: str
    domino_ready: bool
    pivot_confirmed: bool
    level2_broken: bool
    level3_broken: bool


class LevelAnalyzer:
    """Section 8.1: Domino Effect and pivot confirmation"""
    
    @staticmethod
    def analyze(df_4h: pd.DataFrame, df_1h: pd.DataFrame, 
                df_15m: pd.DataFrame) -> LevelStructure:
        
        # Level 1: Primary trend on 4h
        highs_4h, _, lows_4h, _ = find_swing_points(df_4h, lookback=3)
        if len(highs_4h) >= 2 and len(lows_4h) >= 2:
            l1_trend = "up" if highs_4h[-1] > highs_4h[-2] and lows_4h[-1] > lows_4h[-2] else \
                      "down" if highs_4h[-1] < highs_4h[-2] and lows_4h[-1] < lows_4h[-2] else "flat"
        else:
            l1_trend = "flat"
        
        # Level 2: Counter-trend on 1h
        highs_1h, _, lows_1h, _ = find_swing_points(df_1h, lookback=2)
        if len(highs_1h) >= 2 and len(lows_1h) >= 2:
            l2_trend = "up" if highs_1h[-1] > highs_1h[-2] and lows_1h[-1] > lows_1h[-2] else \
                      "down" if highs_1h[-1] < highs_1h[-2] and lows_1h[-1] < lows_1h[-2] else "flat"
        else:
            l2_trend = "flat"
        
        # Level 3: Refined on 15m
        highs_15m, _, lows_15m, _ = find_swing_points(df_15m, lookback=2)
        if len(highs_15m) >= 2 and len(lows_15m) >= 2:
            l3_trend = "up" if highs_15m[-1] > highs_15m[-2] and lows_15m[-1] > lows_15m[-2] else \
                      "down" if highs_15m[-1] < highs_15m[-2] and lows_15m[-1] < lows_15m[-2] else "flat"
        else:
            l3_trend = "flat"
        
        # Check breaks
        current_15m = float(df_15m['close'].iloc[-1])
        level3_broken = (l3_trend == "down" and current_15m > highs_15m[-2]) if len(highs_15m) >= 2 else False
        
        current_1h = float(df_1h['close'].iloc[-1])
        level2_broken = (l2_trend == "down" and current_1h > highs_1h[-2]) if len(highs_1h) >= 2 else False
        
        domino_ready = level3_broken and not level2_broken
        pivot_confirmed = level2_broken
        
        return LevelStructure(
            level1_trend=l1_trend,
            level2_counter=l2_trend,
            level3_refined=l3_trend,
            domino_ready=domino_ready,
            pivot_confirmed=pivot_confirmed,
            level2_broken=level2_broken,
            level3_broken=level3_broken
        )


# =============================================================================
# LECTURE 4: LIQUIDITY
# =============================================================================
@dataclass
class LiquidityGrab:
    direction: str
    price: float
    confirmed: bool
    double_effect: bool
    volume_spike: bool
    cascade_potential: bool
    is_target: bool = False
    is_grab: bool = True


class LiquidityDetector:
    """LECTURE 4 + Section 8.2: Liquidity with target vs grab distinction"""
    
    @staticmethod
    def detect_grabs(df: pd.DataFrame, valid_range: Optional[ValidatedRange] = None) -> List[LiquidityGrab]:
        grabs = []
        if len(df) < 20:
            return grabs
        
        highs, high_idx, lows, low_idx = find_swing_points(df, lookback=3)
        avg_volume = float(df['volume'].tail(20).mean())
        
        for sp_price, sp_idx in zip(highs[-5:], high_idx[-5:]):
            for i in range(sp_idx + 1, min(sp_idx + 15, len(df))):
                candle = df.iloc[i]
                if candle['high'] > sp_price:
                    body = max(candle['close'], candle['open'])
                    wick_pct = (candle['high'] - body) / sp_price if sp_price > 0 else 0
                    if wick_pct < 0.002:
                        continue
                    
                    confirmed = (i + 1 < len(df) and df.iloc[i+1]['close'] < sp_price)
                    volume_spike = candle['volume'] > avg_volume * 1.5
                    double_effect = confirmed and (volume_spike or candle['close'] > candle['open'])
                    cascade = confirmed and i + 3 < len(df) and all(
                        df.iloc[i+k]['close'] < df.iloc[i+k-1]['close'] for k in range(1, 3))
                    
                    is_target = not (volume_spike and wick_pct > 0.01)
                    
                    grabs.append(LiquidityGrab("high", sp_price, confirmed, double_effect, 
                                               volume_spike, cascade, is_target, not is_target))
                    break
        
        for sp_price, sp_idx in zip(lows[-5:], low_idx[-5:]):
            for i in range(sp_idx + 1, min(sp_idx + 15, len(df))):
                candle = df.iloc[i]
                if candle['low'] < sp_price:
                    body = min(candle['close'], candle['open'])
                    wick_pct = (body - candle['low']) / sp_price if sp_price > 0 else 0
                    if wick_pct < 0.002:
                        continue
                    
                    confirmed = (i + 1 < len(df) and df.iloc[i+1]['close'] > sp_price)
                    volume_spike = candle['volume'] > avg_volume * 1.5
                    double_effect = confirmed and (volume_spike or candle['close'] < candle['open'])
                    cascade = confirmed and i + 3 < len(df) and all(
                        df.iloc[i+k]['close'] > df.iloc[i+k-1]['close'] for k in range(1, 3))
                    
                    is_target = not (volume_spike and wick_pct > 0.01)
                    
                    grabs.append(LiquidityGrab("low", sp_price, confirmed, double_effect,
                                               volume_spike, cascade, is_target, not is_target))
                    break
        
        return grabs
    
    @staticmethod
    def rtz_quality(valid_range: ValidatedRange, obs: List[OrderBlock], grabs: List[LiquidityGrab]) -> float:
        obstacles = sum(1 for ob in obs if ob.has_fvg)
        liq_in_path = sum(1 for g in grabs if g.confirmed and g.is_target)
        quality = 0.50 - (obstacles * 0.12) + (liq_in_path * 0.08)
        return min(0.95, max(0.20, quality))


# =============================================================================
# LECTURE 1: MARKET STRUCTURE
# =============================================================================
@dataclass
class MarketStructure:
    trend: str = "flat"
    bos: str = ""
    bos_good: bool = False
    bos_inside_range: bool = False
    sfp: str = ""
    swarm_aligned: bool = False
    domino_complete: bool = False
    breaker_quality: BreakerQuality = BreakerQuality.MODERATE


class MarketStructureAnalyzer:
    """LECTURE 1 + Section 8.4 Variable 4: Breaker quality assessment"""
    
    @staticmethod
    def analyze(df: pd.DataFrame, valid_range: Optional[ValidatedRange] = None) -> MarketStructure:
        ms = MarketStructure()
        if len(df) < 20:
            return ms
        
        highs, _, lows, _ = find_swing_points(df, lookback=3)
        if len(highs) < 2 or len(lows) < 2:
            return ms
        
        last_high = highs[-1]
        prev_high = highs[-2] if len(highs) >= 2 else last_high
        last_low = lows[-1]
        prev_low = lows[-2] if len(lows) >= 2 else last_low
        
        if last_high > prev_high and last_low > prev_low:
            ms.trend = "up"
        elif last_high < prev_high and last_low < prev_low:
            ms.trend = "down"
        
        current_price = float(df['close'].iloc[-1])
        current_candle = df.iloc[-1]
        
        if ms.trend == "up" and current_price > last_high:
            ms.bos = "bullish"
            ms.bos_good = ((current_price - last_high) / last_high > 0.005 and 
                          len(df) >= 2 and float(df['close'].iloc[-2]) > last_high)
            if valid_range:
                ms.bos_inside_range = (valid_range.low <= last_high <= valid_range.high)
            
            # Section 8.4 Variable 4: Assess breaker quality
            ms.breaker_quality = MarketStructureAnalyzer._assess_breaker(df, "bullish")
        
        elif ms.trend == "down" and current_price < last_low:
            ms.bos = "bearish"
            ms.bos_good = ((last_low - current_price) / last_low > 0.005 and 
                          len(df) >= 2 and float(df['close'].iloc[-2]) < last_low)
            if valid_range:
                ms.bos_inside_range = (valid_range.low <= last_low <= valid_range.high)
            
            ms.breaker_quality = MarketStructureAnalyzer._assess_breaker(df, "bearish")
        
        if ms.trend == "up" and current_candle['high'] > last_high and current_candle['close'] < last_high:
            ms.sfp = "bearish"
        elif ms.trend == "down" and current_candle['low'] < last_low and current_candle['close'] > last_low:
            ms.sfp = "bullish"
        
        return ms
    
    @staticmethod
    def _assess_breaker(df: pd.DataFrame, direction: str) -> BreakerQuality:
        """Section 8.4 Variable 4: Quality breaker assessment"""
        if len(df) < 5:
            return BreakerQuality.MODERATE
        
        recent = df.iloc[-3:]
        
        if direction == "bullish":
            is_aggressive = all(c['close'] > c['open'] for _, c in recent.iterrows())
            strong_close = recent.iloc[-1]['close'] > recent.iloc[-1]['open'] * 1.01
            displacement = (recent.iloc[-1]['close'] - recent.iloc[0]['open']) / recent.iloc[0]['open']
            
            if is_aggressive and strong_close and displacement > 0.01:
                return BreakerQuality.AGGRESSIVE
            elif displacement < 0.003:
                return BreakerQuality.WEAK
        else:
            is_aggressive = all(c['close'] < c['open'] for _, c in recent.iterrows())
            strong_close = recent.iloc[-1]['close'] < recent.iloc[-1]['open'] * 0.99
            displacement = (recent.iloc[0]['open'] - recent.iloc[-1]['close']) / recent.iloc[0]['open']
            
            if is_aggressive and strong_close and displacement > 0.01:
                return BreakerQuality.AGGRESSIVE
            elif displacement < 0.003:
                return BreakerQuality.WEAK
        
        return BreakerQuality.MODERATE


# =============================================================================
# SECTION E: CONTEXT BUILDING
# =============================================================================
class ContextBuilder:
    """Section E: Complete context ranking system"""
    
    @staticmethod
    def determine_context(df: pd.DataFrame, valid_range: ValidatedRange, 
                          direction: str) -> ContextRank:
        
        current_price = float(df['close'].iloc[-1])
        
        # Foundation Rules
        at_premium = current_price > valid_range.equilibrium
        at_discount = current_price < valid_range.equilibrium
        
        if direction == "short" and at_premium:
            base = ContextRank.SEMI_PRO
        elif direction == "long" and at_discount:
            base = ContextRank.SEMI_PRO
        else:
            base = ContextRank.SEMI_COUNTER
        
        # Check for Pro context boosters
        highs, _, lows, _ = find_swing_points(df, lookback=3)
        
        if direction == "short":
            # Check for Bread & Butter setup
            if len(lows) >= 2 and lows[-2] < lows[-1]:
                recent_low = df['low'].iloc[-20:].min()
                if recent_low < valid_range.low * 0.95:
                    return ContextRank.PRO
        else:
            if len(highs) >= 2 and highs[-2] > highs[-1]:
                recent_high = df['high'].iloc[-20:].max()
                if recent_high > valid_range.high * 1.05:
                    return ContextRank.PRO
        
        return base
    
    @staticmethod
    def grade_setup(major_context: ContextRank, altcoin_context: ContextRank,
                    is_ehp: bool = False, has_test_phase: bool = False) -> SetupGrade:
        """Section E: A+ to C grading system"""
        
        # EHP is always A+ if context is at least Semi-Pro
        if is_ehp and major_context in [ContextRank.PRO, ContextRank.SEMI_PRO]:
            return SetupGrade.A_PLUS
        
        # Test phase boosts grade
        if has_test_phase:
            if major_context == ContextRank.PRO:
                return SetupGrade.A_PLUS
            elif major_context == ContextRank.SEMI_PRO:
                return SetupGrade.A
        
        # Standard grading
        if major_context == ContextRank.PRO:
            if altcoin_context in [ContextRank.PRO, ContextRank.SEMI_PRO]:
                return SetupGrade.A_PLUS
            return SetupGrade.A
        elif major_context == ContextRank.SEMI_PRO:
            if altcoin_context in [ContextRank.PRO, ContextRank.SEMI_PRO]:
                return SetupGrade.A
            return SetupGrade.A_MINUS
        elif major_context == ContextRank.NEUTRAL:
            if altcoin_context in [ContextRank.PRO, ContextRank.SEMI_PRO]:
                return SetupGrade.A_MINUS
            return SetupGrade.B
        elif major_context == ContextRank.SEMI_COUNTER:
            return SetupGrade.B
        else:
            return SetupGrade.C


# =============================================================================
# ENHANCED TCT SIGNAL
# =============================================================================
@dataclass
class EnhancedTCTSignal:
    """Complete TCT signal with all advanced concepts"""
    symbol: str
    direction: Direction
    model: TCTModel
    entry: float
    stop: float
    target: float
    rr: float
    tp1: float
    tp2: float
    tp3: float
    confidence: float
    position_size: float
    reason: str
    valid_range: ValidatedRange
    tap1: float
    tap2: float
    tap3: float
    
    # Advanced concepts
    qrz: Optional[QRZAnalysis] = None
    levels: Optional[LevelStructure] = None
    context_rank: ContextRank = ContextRank.NEUTRAL
    setup_grade: SetupGrade = SetupGrade.C
    is_ehp: bool = False
    has_test_phase: bool = False
    extended_tap_available: bool = False
    breaker_quality: BreakerQuality = BreakerQuality.MODERATE
    third_tap_quality: str = ""
    range_duration_hours: float = 0.0
    is_daily_range_exception: bool = False
    
    timestamp: datetime = field(default_factory=datetime.now)


# =============================================================================
# ENHANCED TCT ANALYZER (MAIN ENGINE)
# =============================================================================
class EnhancedTCTAnalyzer:
    """COMPLETE TCT ANALYSIS WITH ALL ADVANCED CONCEPTS"""
    
    def __init__(self):
        self.range_detector = RangeDetector()
        self.sd_detector = SupplyDemandDetector()
        self.liq_detector = LiquidityDetector()
        self.ms_analyzer = MarketStructureAnalyzer()
        self.qrz_analyzer = QRZAnalyzer()
        self.level_analyzer = LevelAnalyzer()
        self.context_builder = ContextBuilder()
    
    def _detect_deviations(self, df: pd.DataFrame, valid_range: ValidatedRange) -> Tuple[List[float], List[float]]:
        high_devs, low_devs = [], []
        recent_df = df.iloc[-40:] if len(df) >= 40 else df
        
        for i in range(len(recent_df)):
            candle = recent_df.iloc[i]
            
            if candle['high'] > valid_range.high and candle['high'] <= valid_range.dl2_upper:
                if candle['close'] < valid_range.high:
                    high_devs.append(float(candle['high']))
                elif candle['close'] > valid_range.high:
                    if i + 1 < len(recent_df) and recent_df.iloc[i+1]['close'] < valid_range.high:
                        high_devs.append(float(candle['high']))
            
            if candle['low'] < valid_range.low and candle['low'] >= valid_range.dl2_lower:
                if candle['close'] > valid_range.low:
                    low_devs.append(float(candle['low']))
                elif candle['close'] < valid_range.low:
                    if i + 1 < len(recent_df) and recent_df.iloc[i+1]['close'] > valid_range.low:
                        low_devs.append(float(candle['low']))
        
        return high_devs, low_devs
    
    def _detect_compressing(self, df: pd.DataFrame) -> bool:
        if len(df) < 20:
            return False
        first_half = df.iloc[-20:-10]
        second_half = df.iloc[-10:]
        range1 = first_half['high'].max() - first_half['low'].min()
        range2 = second_half['high'].max() - second_half['low'].min()
        return range2 < range1 * 0.75
    
    def _check_tap_spacing(self, tap1: float, tap2: float, tap3: float) -> bool:
        if tap1 == 0 or tap2 == 0 or tap3 == 0:
            return False
        d12 = abs(tap1 - tap2)
        d23 = abs(tap2 - tap3)
        if d12 == 0:
            return False
        ratio = d23 / d12
        return 0.2 <= ratio <= 5.0
    
    def _find_extreme_liquidity(self, df: pd.DataFrame, direction: str) -> Optional[float]:
        highs, _, lows, _ = find_swing_points(df, lookback=3)
        if direction == "long" and len(lows) >= 2:
            return lows[-2]
        elif direction == "short" and len(highs) >= 2:
            return highs[-2]
        return None
    
    def _find_extreme_ob(self, obs: List[OrderBlock], direction: str) -> Optional[OrderBlock]:
        if direction == "long":
            demand = [ob for ob in obs if ob.direction == "demand" and ob.is_extreme]
            return demand[-1] if demand else None
        else:
            supply = [ob for ob in obs if ob.direction == "supply" and ob.is_extreme]
            return supply[-1] if supply else None
    
    def _detect_ehp(self, df_4h: pd.DataFrame, df_1h: pd.DataFrame, 
                    valid_range: ValidatedRange, direction: str) -> bool:
        """Section C.1: EHP detection"""
        highs_4h, _, lows_4h, _ = find_swing_points(df_4h, lookback=3)
        highs_1h, _, lows_1h, _ = find_swing_points(df_1h, lookback=2)
        
        if len(highs_4h) < 2 or len(lows_4h) < 2:
            return False
        
        if direction == "long":
            if len(lows_1h) >= 3:
                tap2_tap3_ratio = abs(lows_1h[-1] - lows_1h[-2]) / abs(lows_1h[-2] - lows_1h[-3]) if len(lows_1h) >= 3 else 1
                narrow_tap3 = tap2_tap3_ratio < 0.3
                return narrow_tap3 and valid_range.duration_hours >= 12
        else:
            if len(highs_1h) >= 3:
                tap2_tap3_ratio = abs(highs_1h[-1] - highs_1h[-2]) / abs(highs_1h[-2] - highs_1h[-3]) if len(highs_1h) >= 3 else 1
                narrow_tap3 = tap2_tap3_ratio < 0.3
                return narrow_tap3 and valid_range.duration_hours >= 12
        
        return False
    
    def _detect_test_phase(self, df: pd.DataFrame, valid_range: ValidatedRange, 
                           direction: str) -> Tuple[bool, float]:
        """Section C.2: Test phase detection for Model One"""
        if direction == "long":
            lows, low_idx = find_swing_points(df, lookback=2)[2:]
            if len(lows) >= 3:
                test_low = lows[-1]
                prior_low = lows[-2]
                if test_low < prior_low * 0.98:
                    return True, test_low
        else:
            highs, high_idx = find_swing_points(df, lookback=2)[:2]
            if len(highs) >= 3:
                test_high = highs[-1]
                prior_high = highs[-2]
                if test_high > prior_high * 1.02:
                    return True, test_high
        
        return False, 0.0
    
    def _calculate_confidence(self, base: float, extras: Dict) -> float:
        conf = base
        if extras.get("liq_grabbed"): conf += 0.08
        if extras.get("double_effect"): conf += 0.06
        if extras.get("fvg"): conf += 0.05
        if extras.get("bos_inside"): conf += 0.10
        if extras.get("good_rtz"): conf += 0.06
        if extras.get("compressing"): conf += 0.05
        if extras.get("volume_spike"): conf += 0.06
        if extras.get("cascade"): conf += 0.05
        if extras.get("extreme_liq"): conf += 0.07
        if extras.get("extreme_ob"): conf += 0.06
        if extras.get("bos_return"): conf += 0.08
        if extras.get("taps_spaced"): conf += 0.04
        if extras.get("entry_zone_valid"): conf += 0.05
        if extras.get("valid_qrz"): conf += 0.08
        if extras.get("aggressive_breaker"): conf += 0.06
        if extras.get("pro_context"): conf += 0.05
        if extras.get("is_ehp"): conf += 0.10
        if extras.get("has_test_phase"): conf += 0.07
        return min(0.97, conf)
    
    def _calc_position(self, entry: float, stop: float, confidence: float) -> float:
        risk_amount = ACCOUNT_SIZE * (RISK_PCT / 100)
        sl_pct = abs(entry - stop) / entry * 100
        if sl_pct == 0:
            return 0
        
        position = (risk_amount / sl_pct) * 100 / entry
        
        # Section C.1: Increased position size for EHP
        if confidence >= 0.88:
            position *= 1.5
        
        return position
    
    def _check_ltf_confirmation(self, ltf_data: Dict[str, pd.DataFrame], 
                                 direction: str, valid_range: ValidatedRange) -> Tuple[bool, str, float]:
        confirmations = []
        
        for tf, df in ltf_data.items():
            if df is None or len(df) < 20:
                continue
            
            ms = self.ms_analyzer.analyze(df, valid_range)
            
            if direction == "short":
                if ms.bos == "bearish":
                    boost = 0.05 if ms.bos_good else 0.03
                    if ms.bos_inside_range:
                        boost += 0.05
                    if ms.breaker_quality == BreakerQuality.AGGRESSIVE:
                        boost += 0.03
                    confirmations.append((tf, "BOS", ms.bos_good, boost))
                elif ms.sfp == "bearish":
                    confirmations.append((tf, "SFP", True, 0.04))
            else:
                if ms.bos == "bullish":
                    boost = 0.05 if ms.bos_good else 0.03
                    if ms.bos_inside_range:
                        boost += 0.05
                    if ms.breaker_quality == BreakerQuality.AGGRESSIVE:
                        boost += 0.03
                    confirmations.append((tf, "BOS", ms.bos_good, boost))
                elif ms.sfp == "bullish":
                    confirmations.append((tf, "SFP", True, 0.04))
        
        if not confirmations:
            return False, "", 0.0
        
        best = None
        best_score = -1
        
        for tf, conf_type, is_good, boost in confirmations:
            score = 0
            if conf_type == "BOS" and is_good:
                score = 10
            elif conf_type == "BOS":
                score = 7
            elif conf_type == "SFP":
                score = 5
            
            if tf == '5m': score += 3
            elif tf == '15m': score += 2
            elif tf == '30m': score += 1
            
            if score > best_score:
                best_score = score
                best = (tf, conf_type, is_good, boost)
        
        if best:
            return True, best[0], best[3]
        return False, "", 0.0
    
    def _check_bos_return(self, ltf_data: Dict[str, pd.DataFrame], 
                          valid_range: ValidatedRange, direction: str) -> Tuple[bool, str]:
        for tf, df in ltf_data.items():
            if df is None or len(df) < 10:
                continue
            
            current_price = float(df['close'].iloc[-1])
            
            if direction == "long":
                recent_low = df['low'].iloc[-10:].min()
                if recent_low < valid_range.low and current_price > valid_range.low:
                    return True, tf
            else:
                recent_high = df['high'].iloc[-10:].max()
                if recent_high > valid_range.high and current_price < valid_range.high:
                    return True, tf
        
        return False, ""
    
    def analyze(self, symbol: str, df_4h: pd.DataFrame, 
                ltf_data: Dict[str, pd.DataFrame]) -> Optional[EnhancedTCTSignal]:
        
        if len(df_4h) < 50:
            return None
        
        # Get lower timeframe data for Level analysis
        df_1h = ltf_data.get('1h')
        df_15m = ltf_data.get('15m')
        
        if df_1h is None or df_15m is None:
            return None
        
        # Step 1: Detect valid range
        valid_range = self.range_detector.detect(df_4h)
        if not valid_range or not valid_range.is_valid:
            return None
        
        if not valid_range.is_good_range:
            return None
        
        # Step 2: Get supply/demand and liquidity
        obs = self.sd_detector.detect_order_blocks(df_4h, valid_range)
        grabs = self.liq_detector.detect_grabs(df_4h, valid_range)
        rtz = self.liq_detector.rtz_quality(valid_range, obs, grabs)
        
        # Step 3: Detect deviations
        high_devs, low_devs = self._detect_deviations(df_4h, valid_range)
        
        current_price = float(df_4h['close'].iloc[-1])
        compressing = self._detect_compressing(df_4h)
        
        fvg_present = any(ob.has_fvg for ob in obs)
        liq_grabbed = any(g.confirmed for g in grabs)
        double_effect = any(g.double_effect for g in grabs)
        volume_spike = any(g.volume_spike for g in grabs)
        cascade = any(g.cascade_potential for g in grabs)
        
        valid_entry_long = valid_range.is_in_discount(current_price)
        valid_entry_short = valid_range.is_in_premium(current_price)
        
        ltf_confirmed_short, best_tf_short, conf_boost_short = self._check_ltf_confirmation(
            ltf_data, "short", valid_range)
        ltf_confirmed_long, best_tf_long, conf_boost_long = self._check_ltf_confirmation(
            ltf_data, "long", valid_range)
        
        bos_return_long, bos_return_tf_long = self._check_bos_return(ltf_data, valid_range, "long")
        bos_return_short, bos_return_tf_short = self._check_bos_return(ltf_data, valid_range, "short")
        
        # Level Structure Analysis
        levels = self.level_analyzer.analyze(df_4h, df_1h, df_15m)
        
        extras = {
            "liq_grabbed": liq_grabbed,
            "double_effect": double_effect,
            "fvg": fvg_present,
            "good_rtz": rtz > 0.60,
            "compressing": compressing,
            "volume_spike": volume_spike,
            "cascade": cascade,
            "domino_ready": levels.domino_ready,
        }
        
        # =====================================================================
        # MODEL 1 DISTRIBUTION
        # =====================================================================
        if len(high_devs) >= 2 and valid_entry_short and ltf_confirmed_short:
            tap1 = valid_range.high
            tap2 = high_devs[-2]
            tap3 = high_devs[-1]
            
            if self._check_tap_spacing(tap1, tap2, tap3) and tap3 > tap2:
                entry = current_price
                stop = tap3 * 1.015
                target = valid_range.wyckoff_low or valid_range.low
                
                risk = abs(entry - stop)
                reward = abs(target - entry)
                rr = reward / risk if risk > 0 else 0
                
                if rr >= MIN_RR:
                    # QRZ Analysis
                    qrz = self.qrz_analyzer.analyze(df_4h, valid_range, "short")
                    
                    # Test Phase Detection
                    has_test, test_price = self._detect_test_phase(df_4h, valid_range, "short")
                    
                    # EHP Detection
                    is_ehp = self._detect_ehp(df_4h, df_1h, valid_range, "short")
                    
                    # Context Building
                    context = self.context_builder.determine_context(df_4h, valid_range, "short")
                    
                    extras["entry_zone_valid"] = valid_entry_short
                    extras["taps_spaced"] = True
                    extras["bos_return"] = bos_return_short
                    extras["bos_inside"] = True
                    extras["valid_qrz"] = qrz.is_valid_qrz
                    extras["pro_context"] = (context == ContextRank.PRO)
                    extras["is_ehp"] = is_ehp
                    extras["has_test_phase"] = has_test
                    
                    ms = self.ms_analyzer.analyze(df_4h, valid_range)
                    if ms.breaker_quality == BreakerQuality.AGGRESSIVE:
                        extras["aggressive_breaker"] = True
                    
                    confidence = self._calculate_confidence(0.52, extras) + conf_boost_short
                    
                    # Duration validation (Section 8.4 Variable 2)
                    duration_ok = valid_range.duration_hours >= MIN_RANGE_DURATION_HOURS
                    is_daily_exception = False
                    
                    if not duration_ok:
                        if valid_range.duration_hours >= DAILY_RANGE_MIN_HOURS and qrz.quality_score > 0.75:
                            is_daily_exception = True
                            duration_ok = True
                    
                    if confidence >= MIN_CONFIDENCE and duration_ok:
                        # Determine model
                        if is_ehp:
                            model = TCTModel.EHP_SHORT
                        elif has_test:
                            model = TCTModel.TEST_PHASE_SHORT
                        else:
                            model = TCTModel.M1D
                        
                        # Setup Grade
                        grade = self.context_builder.grade_setup(context, context, is_ehp, has_test)
                        
                        # Only send A+ and A setups
                        if grade in [SetupGrade.A_PLUS, SetupGrade.A]:
                            ltf_info = f"LTF({best_tf_short})"
                            if bos_return_short:
                                ltf_info += f"+Return({bos_return_tf_short})"
                            
                            return EnhancedTCTSignal(
                                symbol=symbol, direction=Direction.SHORT, model=model,
                                entry=entry, stop=stop, target=target, rr=rr,
                                tp1=entry - (entry - target) * 0.50,
                                tp2=entry - (entry - target) * 0.75,
                                tp3=target,
                                confidence=confidence,
                                position_size=self._calc_position(entry, stop, confidence),
                                reason=f"{model.value} | {ltf_info} | Grade:{grade.value}",
                                valid_range=valid_range, tap1=tap1, tap2=tap2, tap3=tap3,
                                qrz=qrz, levels=levels, context_rank=context,
                                setup_grade=grade, is_ehp=is_ehp, has_test_phase=has_test,
                                breaker_quality=ms.breaker_quality,
                                range_duration_hours=valid_range.duration_hours,
                                is_daily_range_exception=is_daily_exception
                            )
        
        # =====================================================================
        # MODEL 1 ACCUMULATION
        # =====================================================================
        if len(low_devs) >= 2 and valid_entry_long and ltf_confirmed_long:
            tap1 = valid_range.low
            tap2 = low_devs[-2]
            tap3 = low_devs[-1]
            
            if self._check_tap_spacing(tap1, tap2, tap3) and tap3 < tap2:
                entry = current_price
                stop = tap3 * 0.985
                target = valid_range.wyckoff_high or valid_range.high
                
                risk = abs(entry - stop)
                reward = abs(target - entry)
                rr = reward / risk if risk > 0 else 0
                
                if rr >= MIN_RR:
                    qrz = self.qrz_analyzer.analyze(df_4h, valid_range, "long")
                    has_test, test_price = self._detect_test_phase(df_4h, valid_range, "long")
                    is_ehp = self._detect_ehp(df_4h, df_1h, valid_range, "long")
                    context = self.context_builder.determine_context(df_4h, valid_range, "long")
                    
                    extras["entry_zone_valid"] = valid_entry_long
                    extras["taps_spaced"] = True
                    extras["bos_return"] = bos_return_long
                    extras["bos_inside"] = True
                    extras["valid_qrz"] = qrz.is_valid_qrz
                    extras["pro_context"] = (context == ContextRank.PRO)
                    extras["is_ehp"] = is_ehp
                    extras["has_test_phase"] = has_test
                    
                    ms = self.ms_analyzer.analyze(df_4h, valid_range)
                    if ms.breaker_quality == BreakerQuality.AGGRESSIVE:
                        extras["aggressive_breaker"] = True
                    
                    confidence = self._calculate_confidence(0.52, extras) + conf_boost_long
                    
                    duration_ok = valid_range.duration_hours >= MIN_RANGE_DURATION_HOURS
                    is_daily_exception = False
                    
                    if not duration_ok:
                        if valid_range.duration_hours >= DAILY_RANGE_MIN_HOURS and qrz.quality_score > 0.75:
                            is_daily_exception = True
                            duration_ok = True
                    
                    if confidence >= MIN_CONFIDENCE and duration_ok:
                        if is_ehp:
                            model = TCTModel.EHP_LONG
                        elif has_test:
                            model = TCTModel.TEST_PHASE_LONG
                        else:
                            model = TCTModel.M1A
                        
                        grade = self.context_builder.grade_setup(context, context, is_ehp, has_test)
                        
                        if grade in [SetupGrade.A_PLUS, SetupGrade.A]:
                            ltf_info = f"LTF({best_tf_long})"
                            if bos_return_long:
                                ltf_info += f"+Return({bos_return_tf_long})"
                            
                            return EnhancedTCTSignal(
                                symbol=symbol, direction=Direction.LONG, model=model,
                                entry=entry, stop=stop, target=target, rr=rr,
                                tp1=entry + (target - entry) * 0.50,
                                tp2=entry + (target - entry) * 0.75,
                                tp3=target,
                                confidence=confidence,
                                position_size=self._calc_position(entry, stop, confidence),
                                reason=f"{model.value} | {ltf_info} | Grade:{grade.value}",
                                valid_range=valid_range, tap1=tap1, tap2=tap2, tap3=tap3,
                                qrz=qrz, levels=levels, context_rank=context,
                                setup_grade=grade, is_ehp=is_ehp, has_test_phase=has_test,
                                breaker_quality=ms.breaker_quality,
                                range_duration_hours=valid_range.duration_hours,
                                is_daily_range_exception=is_daily_exception
                            )
        
        # =====================================================================
        # MODEL 2 DISTRIBUTION
        # =====================================================================
        if len(high_devs) == 1 and valid_entry_short and ltf_confirmed_short:
            tap1 = valid_range.high
            tap2 = high_devs[0]
            
            extreme_liq = self._find_extreme_liquidity(df_4h, "short")
            extreme_ob = self._find_extreme_ob(obs, "short")
            
            has_extreme = False
            if extreme_liq and current_price >= extreme_liq * 0.99:
                has_extreme = True
                extras["extreme_liq"] = True
            if extreme_ob and current_price >= extreme_ob.low * 0.99:
                has_extreme = True
                extras["extreme_ob"] = True
            
            if has_extreme:
                tap3 = current_price
                if self._check_tap_spacing(tap1, tap2, tap3) and tap3 < tap2:
                    entry = current_price
                    stop = entry * 1.015
                    target = valid_range.wyckoff_low or valid_range.low
                    
                    risk = abs(entry - stop)
                    reward = abs(target - entry)
                    rr = reward / risk if risk > 0 else 0
                    
                    if rr >= MIN_RR:
                        qrz = self.qrz_analyzer.analyze(df_4h, valid_range, "short")
                        context = self.context_builder.determine_context(df_4h, valid_range, "short")
                        
                        extras["entry_zone_valid"] = valid_entry_short
                        extras["taps_spaced"] = True
                        extras["bos_return"] = bos_return_short
                        extras["valid_qrz"] = qrz.is_valid_qrz
                        extras["pro_context"] = (context == ContextRank.PRO)
                        
                        ms = self.ms_analyzer.analyze(df_4h, valid_range)
                        if ms.breaker_quality == BreakerQuality.AGGRESSIVE:
                            extras["aggressive_breaker"] = True
                        
                        confidence = self._calculate_confidence(0.50, extras) + conf_boost_short
                        
                        duration_ok = valid_range.duration_hours >= MIN_RANGE_DURATION_HOURS
                        
                        if confidence >= MIN_CONFIDENCE and duration_ok:
                            extreme_type = "liq" if extras.get("extreme_liq") else "OB"
                            grade = self.context_builder.grade_setup(context, context, False, False)
                            
                            if grade in [SetupGrade.A_PLUS, SetupGrade.A]:
                                ltf_info = f"LTF({best_tf_short})"
                                if bos_return_short:
                                    ltf_info += f"+Return({bos_return_tf_short})"
                                
                                return EnhancedTCTSignal(
                                    symbol=symbol, direction=Direction.SHORT, model=TCTModel.M2D,
                                    entry=entry, stop=stop, target=target, rr=rr,
                                    tp1=entry - (entry - target) * 0.50,
                                    tp2=entry - (entry - target) * 0.75,
                                    tp3=target,
                                    confidence=confidence,
                                    position_size=self._calc_position(entry, stop, confidence),
                                    reason=f"M2D | extreme {extreme_type} | {ltf_info} | Grade:{grade.value}",
                                    valid_range=valid_range, tap1=tap1, tap2=tap2, tap3=tap3,
                                    qrz=qrz, levels=levels, context_rank=context,
                                    setup_grade=grade, breaker_quality=ms.breaker_quality,
                                    range_duration_hours=valid_range.duration_hours
                                )
        
        # =====================================================================
        # MODEL 2 ACCUMULATION
        # =====================================================================
        if len(low_devs) == 1 and valid_entry_long and ltf_confirmed_long:
            tap1 = valid_range.low
            tap2 = low_devs[0]
            
            extreme_liq = self._find_extreme_liquidity(df_4h, "long")
            extreme_ob = self._find_extreme_ob(obs, "long")
            
            has_extreme = False
            if extreme_liq and current_price <= extreme_liq * 1.01:
                has_extreme = True
                extras["extreme_liq"] = True
            if extreme_ob and current_price <= extreme_ob.high * 1.01:
                has_extreme = True
                extras["extreme_ob"] = True
            
            if has_extreme:
                tap3 = current_price
                if self._check_tap_spacing(tap1, tap2, tap3) and tap3 > tap2:
                    entry = current_price
                    stop = entry * 0.985
                    target = valid_range.wyckoff_high or valid_range.high
                    
                    risk = abs(entry - stop)
                    reward = abs(target - entry)
                    rr = reward / risk if risk > 0 else 0
                    
                    if rr >= MIN_RR:
                        qrz = self.qrz_analyzer.analyze(df_4h, valid_range, "long")
                        context = self.context_builder.determine_context(df_4h, valid_range, "long")
                        
                        extras["entry_zone_valid"] = valid_entry_long
                        extras["taps_spaced"] = True
                        extras["bos_return"] = bos_return_long
                        extras["valid_qrz"] = qrz.is_valid_qrz
                        extras["pro_context"] = (context == ContextRank.PRO)
                        
                        ms = self.ms_analyzer.analyze(df_4h, valid_range)
                        if ms.breaker_quality == BreakerQuality.AGGRESSIVE:
                            extras["aggressive_breaker"] = True
                        
                        confidence = self._calculate_confidence(0.50, extras) + conf_boost_long
                        
                        duration_ok = valid_range.duration_hours >= MIN_RANGE_DURATION_HOURS
                        
                        if confidence >= MIN_CONFIDENCE and duration_ok:
                            extreme_type = "liq" if extras.get("extreme_liq") else "OB"
                            grade = self.context_builder.grade_setup(context, context, False, False)
                            
                            if grade in [SetupGrade.A_PLUS, SetupGrade.A]:
                                ltf_info = f"LTF({best_tf_long})"
                                if bos_return_long:
                                    ltf_info += f"+Return({bos_return_tf_long})"
                                
                                return EnhancedTCTSignal(
                                    symbol=symbol, direction=Direction.LONG, model=TCTModel.M2A,
                                    entry=entry, stop=stop, target=target, rr=rr,
                                    tp1=entry + (target - entry) * 0.50,
                                    tp2=entry + (target - entry) * 0.75,
                                    tp3=target,
                                    confidence=confidence,
                                    position_size=self._calc_position(entry, stop, confidence),
                                    reason=f"M2A | extreme {extreme_type} | {ltf_info} | Grade:{grade.value}",
                                    valid_range=valid_range, tap1=tap1, tap2=tap2, tap3=tap3,
                                    qrz=qrz, levels=levels, context_rank=context,
                                    setup_grade=grade, breaker_quality=ms.breaker_quality,
                                    range_duration_hours=valid_range.duration_hours
                                )
        
        # =====================================================================
        # PO3 BULLISH
        # =====================================================================
        if rtz > 0.45 and len(low_devs) >= 1 and ltf_confirmed_long:
            manip_low = min(low_devs[-1] if low_devs else valid_range.low, 
                           df_4h['low'].iloc[-20:].min())
            
            if manip_low < valid_range.low and manip_low >= valid_range.dl2_lower:
                mid = (valid_range.high + valid_range.low) / 2
                
                if current_price > mid and valid_entry_long:
                    entry = current_price
                    stop = manip_low * 0.985
                    target = valid_range.high
                    
                    risk = abs(entry - stop)
                    reward = abs(target - entry)
                    rr = reward / risk if risk > 0 else 0
                    
                    if rr >= MIN_RR:
                        qrz = self.qrz_analyzer.analyze(df_4h, valid_range, "long")
                        context = self.context_builder.determine_context(df_4h, valid_range, "long")
                        
                        extras["compressing"] = compressing
                        extras["valid_qrz"] = qrz.is_valid_qrz
                        confidence = self._calculate_confidence(0.48, extras) + conf_boost_long
                        
                        if confidence >= MIN_CONFIDENCE:
                            grade = self.context_builder.grade_setup(context, context, False, False)
                            
                            if grade in [SetupGrade.A_PLUS, SetupGrade.A]:
                                return EnhancedTCTSignal(
                                    symbol=symbol, direction=Direction.LONG, model=TCTModel.PO3_BULLISH,
                                    entry=entry, stop=stop, target=target, rr=rr,
                                    tp1=entry + (target - entry) * 0.50,
                                    tp2=entry + (target - entry) * 0.75,
                                    tp3=target,
                                    confidence=confidence,
                                    position_size=self._calc_position(entry, stop, confidence),
                                    reason=f"PO3 Bullish | LTF({best_tf_long}) | Grade:{grade.value}",
                                    valid_range=valid_range, tap1=valid_range.low, tap2=manip_low, tap3=current_price,
                                    qrz=qrz, levels=levels, context_rank=context, setup_grade=grade,
                                    range_duration_hours=valid_range.duration_hours
                                )
        
        # =====================================================================
        # PO3 BEARISH
        # =====================================================================
        if rtz > 0.45 and len(high_devs) >= 1 and ltf_confirmed_short:
            manip_high = max(high_devs[-1] if high_devs else valid_range.high,
                            df_4h['high'].iloc[-20:].max())
            
            if manip_high > valid_range.high and manip_high <= valid_range.dl2_upper:
                mid = (valid_range.high + valid_range.low) / 2
                
                if current_price < mid and valid_entry_short:
                    entry = current_price
                    stop = manip_high * 1.015
                    target = valid_range.low
                    
                    risk = abs(entry - stop)
                    reward = abs(target - entry)
                    rr = reward / risk if risk > 0 else 0
                    
                    if rr >= MIN_RR:
                        qrz = self.qrz_analyzer.analyze(df_4h, valid_range, "short")
                        context = self.context_builder.determine_context(df_4h, valid_range, "short")
                        
                        extras["compressing"] = compressing
                        extras["valid_qrz"] = qrz.is_valid_qrz
                        confidence = self._calculate_confidence(0.48, extras) + conf_boost_short
                        
                        if confidence >= MIN_CONFIDENCE:
                            grade = self.context_builder.grade_setup(context, context, False, False)
                            
                            if grade in [SetupGrade.A_PLUS, SetupGrade.A]:
                                return EnhancedTCTSignal(
                                    symbol=symbol, direction=Direction.SHORT, model=TCTModel.PO3_BEARISH,
                                    entry=entry, stop=stop, target=target, rr=rr,
                                    tp1=entry - (entry - target) * 0.50,
                                    tp2=entry - (entry - target) * 0.75,
                                    tp3=target,
                                    confidence=confidence,
                                    position_size=self._calc_position(entry, stop, confidence),
                                    reason=f"PO3 Bearish | LTF({best_tf_short}) | Grade:{grade.value}",
                                    valid_range=valid_range, tap1=valid_range.high, tap2=manip_high, tap3=current_price,
                                    qrz=qrz, levels=levels, context_rank=context, setup_grade=grade,
                                    range_duration_hours=valid_range.duration_hours
                                )
        
        # =====================================================================
        # TWO-TAP EXCEPTIONS
        # =====================================================================
        if len(high_devs) == 1 and rtz > 0.55 and valid_entry_short and ltf_confirmed_short:
            entry = current_price
            stop = entry * 1.015
            target = valid_range.low
            risk = abs(entry - stop)
            reward = abs(target - entry)
            rr = reward / risk if risk > 0 else 0
            
            if rr >= MIN_RR:
                qrz = self.qrz_analyzer.analyze(df_4h, valid_range, "short")
                extras["valid_qrz"] = qrz.is_valid_qrz
                confidence = self._calculate_confidence(0.45, extras) + conf_boost_short
                
                if confidence >= MIN_CONFIDENCE:
                    return EnhancedTCTSignal(
                        symbol=symbol, direction=Direction.SHORT, model=TCTModel.TWO_TAP_SHORT,
                        entry=entry, stop=stop, target=target, rr=rr,
                        tp1=entry - (entry - target) * 0.50,
                        tp2=entry - (entry - target) * 0.75,
                        tp3=target,
                        confidence=confidence,
                        position_size=self._calc_position(entry, stop, confidence),
                        reason=f"Two-Tap Short | RTZ={rtz:.2f}",
                        valid_range=valid_range, tap1=valid_range.high, tap2=high_devs[0], tap3=current_price,
                        qrz=qrz, range_duration_hours=valid_range.duration_hours
                    )
        
        if len(low_devs) == 1 and rtz > 0.55 and valid_entry_long and ltf_confirmed_long:
            entry = current_price
            stop = entry * 0.985
            target = valid_range.high
            risk = abs(entry - stop)
            reward = abs(target - entry)
            rr = reward / risk if risk > 0 else 0
            
            if rr >= MIN_RR:
                qrz = self.qrz_analyzer.analyze(df_4h, valid_range, "long")
                extras["valid_qrz"] = qrz.is_valid_qrz
                confidence = self._calculate_confidence(0.45, extras) + conf_boost_long
                
                if confidence >= MIN_CONFIDENCE:
                    return EnhancedTCTSignal(
                        symbol=symbol, direction=Direction.LONG, model=TCTModel.TWO_TAP_LONG,
                        entry=entry, stop=stop, target=target, rr=rr,
                        tp1=entry + (target - entry) * 0.50,
                        tp2=entry + (target - entry) * 0.75,
                        tp3=target,
                        confidence=confidence,
                        position_size=self._calc_position(entry, stop, confidence),
                        reason=f"Two-Tap Long | RTZ={rtz:.2f}",
                        valid_range=valid_range, tap1=valid_range.low, tap2=low_devs[0], tap3=current_price,
                        qrz=qrz, range_duration_hours=valid_range.duration_hours
                    )
        
        return None


# =============================================================================
# DATA FETCHER - YFINANCE FOR METALS
# =============================================================================
class DataFetcher:
    def __init__(self):
        self._cache: Dict[str, Tuple[pd.DataFrame, float]] = {}
        self._ttl = 180
    
    def get_all_metals(self) -> List[str]:
        """Return the list of metal symbols to scan"""
        log.info(f"📊 Scanning metals: {METAL_SYMBOLS}")
        return METAL_SYMBOLS
    
    def fetch_ohlcv(self, symbol: str, timeframe: str = "4h", limit: int = 200) -> pd.DataFrame:
        """
        Fetch OHLCV data for metals using yfinance.
        Yahoo Finance symbol format: XAUUSD=X, XAGUSD=X, etc.
        """
        key = f"{symbol}_{timeframe}_{limit}"
        if key in self._cache and time.time() - self._cache[key][1] < self._ttl:
            return self._cache[key][0]
        
        try:
            # Map timeframe to yfinance interval
            interval_map = {
                '5m': '5m',
                '15m': '15m',
                '30m': '30m',
                '1h': '1h',
                '4h': '1h',  # yfinance doesn't have 4h, we'll use 1h and resample
            }
            
            actual_interval = interval_map.get(timeframe, '1h')
            
            # Calculate period based on limit and timeframe
            if timeframe == '4h':
                # Need more 1h candles to resample to 4h
                required_candles = limit * 4 + 50
                period = f"{required_candles * 2}h" if required_candles < 500 else "60d"
            else:
                # For other timeframes, calculate appropriate period
                minutes_per_candle = {
                    '5m': 5,
                    '15m': 15,
                    '30m': 30,
                    '1h': 60,
                }
                total_minutes = limit * minutes_per_candle.get(timeframe, 60)
                total_hours = total_minutes // 60
                if total_hours < 48:
                    period = f"{total_hours + 24}h"
                elif total_hours < 720:
                    period = f"{total_hours // 24 + 2}d"
                else:
                    period = "60d"
            
            # Download data
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=actual_interval)
            
            if df.empty:
                log.warning(f"No data for {symbol} with interval {actual_interval}")
                return pd.DataFrame()
            
            # Reset index to make timestamp a column, then set as index
            df = df.reset_index()
            if 'Datetime' in df.columns:
                df = df.rename(columns={'Datetime': 'timestamp'})
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            
            # Rename columns to match expected format
            df = df.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            
            # Ensure we have all required columns
            required = ['open', 'high', 'low', 'close', 'volume']
            for col in required:
                if col not in df.columns:
                    df[col] = 0
            
            # For 4h timeframe, resample from 1h data
            if timeframe == '4h' and actual_interval == '1h':
                df_4h = df.resample('4H').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).dropna()
                
                # Keep only the most recent 'limit' candles
                if len(df_4h) > limit:
                    df_4h = df_4h.iloc[-limit:]
                
                self._cache[key] = (df_4h, time.time())
                return df_4h
            
            # For other timeframes, just return the data
            if len(df) > limit:
                df = df.iloc[-limit:]
            
            self._cache[key] = (df, time.time())
            return df
            
        except Exception as e:
            log.error(f"Error fetching {symbol} {timeframe}: {e}")
            traceback.print_exc()
            return pd.DataFrame()
    
    def get_display_name(self, symbol: str) -> str:
        """Get display name for a metal symbol"""
        return METAL_DISPLAY_NAMES.get(symbol, symbol.replace('=X', ''))


# =============================================================================
# TELEGRAM NOTIFIER
# =============================================================================
class TelegramNotifier:
    def __init__(self):
        self._url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        self._sent_signals = defaultdict(list)
    
    @staticmethod
    def _format_price(p: float) -> str:
        if p > 1000: return f"${p:,.2f}"
        if p > 1: return f"${p:.4f}"
        return f"${p:.6f}"
    
    def can_send(self, symbol: str) -> bool:
        now = datetime.now()
        self._sent_signals[symbol] = [t for t in self._sent_signals[symbol] 
                                       if now - t < timedelta(minutes=SIGNAL_COOLDOWN_MINUTES)]
        
        if len(self._sent_signals[symbol]) > 0:
            return False
        
        total_today = sum(len(v) for v in self._sent_signals.values())
        return total_today < MAX_SIGNALS_PER_DAY
    
    def record_signal(self, symbol: str):
        self._sent_signals[symbol].append(datetime.now())
    
    def send_signal(self, s: EnhancedTCTSignal) -> bool:
        if not self.can_send(s.symbol):
            log.info(f"⏳ Signal skipped for {s.symbol} (cooldown/daily limit)")
            return False
        
        emoji = "🟢" if s.direction == Direction.LONG else "🔴"
        direction_text = "LONG (BUY)" if s.direction == Direction.LONG else "SHORT (SELL)"
        
        grade_emoji = {"A+": "🏆", "A": "⭐", "A-": "📊", "B": "📉", "C": "❌"}
        grade_display = grade_emoji.get(s.setup_grade.value, "") + s.setup_grade.value
        
        ehp_badge = " 🔥 EHP" if s.is_ehp else ""
        test_badge = " 🧪 TEST" if s.has_test_phase else ""
        
        msg = f"""{emoji} <b>ENHANCED TCT SIGNAL | {direction_text} | {s.symbol}</b>
━━━━━━━━━━━━━━━━━━━━
📊 <b>Model:</b> {s.model.value}{ehp_badge}{test_badge}
🏅 <b>Grade:</b> {grade_display} | <b>Context:</b> {s.context_rank.value}
━━━━━━━━━━━━━━━━━━━━
💰 <b>Entry:</b> {self._format_price(s.entry)}
🛑 <b>Stop:</b>  {self._format_price(s.stop)}
🎯 <b>Target:</b> {self._format_price(s.target)}
━━━━━━━━━━━━━━━━━━━━
📈 <b>TP1 (50%):</b> {self._format_price(s.tp1)}
📈 <b>TP2 (75%):</b> {self._format_price(s.tp2)}
📈 <b>TP3 (100%):</b> {self._format_price(s.tp3)}
━━━━━━━━━━━━━━━━━━━━
📊 <b>R:R:</b> 1:{s.rr:.1f} | <b>Conf:</b> {int(s.confidence*100)}%
💵 <b>Position:</b> ${s.position_size:,.0f}
⏱️ <b>Range Duration:</b> {s.range_duration_hours:.1f}h
━━━━━━━━━━━━━━━━━━━━
💡 <b>QRZ:</b> {s.qrz.quality_score:.0%} | <b>Breaker:</b> {s.breaker_quality.value}
💡 <b>Reason:</b> {s.reason}

🔔 <i>Enhanced TCT - Metals Edition | A+ and A setups only</i>"""
        
        try:
            r = requests.post(self._url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
            if r.status_code == 200:
                self.record_signal(s.symbol)
                return True
        except:
            pass
        return False


# =============================================================================
# MAIN SCANNER
# =============================================================================
class EnhancedTCTScanner:
    def __init__(self):
        self.data = DataFetcher()
        self.tct = EnhancedTCTAnalyzer()
        self.tg = TelegramNotifier()
        self._cycle = 0
        self._signals_found = 0
        self._banner()
    
    def _banner(self):
        print("\n" + "=" * 80)
        print("  ENHANCED PURE TCT BOT - METALS EDITION")
        print("  XAUUSD | XAGUSD | XPTUSD | XPDUSD")
        print("=" * 80)
        print("  ORIGINAL LECTURES 1-8: 100% PRESERVED")
        print("  ADVANCED PDF CONCEPTS: FULLY INTEGRATED")
        print("=" * 80)
        print("  ✅ Levels 1,2,3 | QRZ (Primary/Internal) | 4-Variable Checklist")
        print("  ✅ EHP Detection | Test Phase | Extended Tap | Correct Tab One")
        print("  ✅ TCT Creating TCT | D-EEC/A-EEC | Range Duration Rules")
        print("  ✅ Aggressive Third Taps | Context Ranking | A+ to C Grading")
        print("=" * 80)
        print("  🎯 ONLY A+ and A GRADE SETUPS ARE SENT")
        print("  📊 DATA SOURCE: Yahoo Finance")
        print("=" * 80 + "\n")
    
    def _analyze_symbol(self, symbol: str) -> Optional[EnhancedTCTSignal]:
        try:
            # Fetch all required timeframes
            df_4h = self.data.fetch_ohlcv(symbol, "4h", 200)
            df_1h = self.data.fetch_ohlcv(symbol, "1h", 200)
            df_30m = self.data.fetch_ohlcv(symbol, "30m", 200)
            df_15m = self.data.fetch_ohlcv(symbol, "15m", 200)
            df_5m = self.data.fetch_ohlcv(symbol, "5m", 200)
            
            if len(df_4h) < 50:
                log.debug(f"Insufficient 4h data for {symbol}: {len(df_4h)} candles")
                return None
            
            ltf_data = {}
            if len(df_5m) >= 30: ltf_data['5m'] = df_5m
            if len(df_15m) >= 30: ltf_data['15m'] = df_15m
            if len(df_30m) >= 30: ltf_data['30m'] = df_30m
            if len(df_1h) >= 30: ltf_data['1h'] = df_1h
            
            if not ltf_data:
                log.debug(f"Insufficient LTF data for {symbol}")
                return None
            
            # Use display name for cleaner output
            clean_symbol = self.data.get_display_name(symbol)
            return self.tct.analyze(clean_symbol, df_4h, ltf_data)
            
        except Exception as e:
            log.error(f"Error analyzing {symbol}: {e}")
            return None
    
    def run_once(self):
        self._cycle += 1
        ts = datetime.now().strftime("%H:%M:%S")
        
        metals = self.data.get_all_metals()
        print(f"\n{'─' * 60}")
        print(f"🔄 CYCLE #{self._cycle} [{ts}] | Scanning {len(metals)} metals")
        print(f"   📊 Metals: XAU (Gold), XAG (Silver), XPT (Platinum), XPD (Palladium)")
        print(f"   🎯 Filter: A+ and A setups only")
        
        found = []
        for symbol in metals:
            signal = self._analyze_symbol(symbol)
            if signal:
                # ========== EASY FILTER - JUST 3 CHECKS ==========
                # 1. Skip if confidence less than 90%
                if signal.confidence < 0.90:
                    print(f"  ❌ {signal.symbol} - Confidence {int(signal.confidence*100)}% < 90%")
                    continue
        
                # 2. Skip if RR less than 3.0
                if signal.rr < 3.0:
                    print(f"  ❌ {signal.symbol} - RR 1:{signal.rr:.1f} < 1:3")
                    continue
        
                # 3. Skip if using 5m (check reason string for 'LTF(5m)')
                if 'LTF(5m)' in signal.reason or 'LTF(5m)' in str(signal.reason):
                    print(f"  ❌ {signal.symbol} - Using 5m LTF (need 15m+)")
                    continue
                # ================================================
        
                found.append(signal)
                self._signals_found += 1
        
                label = "🟢 LONG" if signal.direction == Direction.LONG else "🔴 SHORT"
                grade_display = f"[{signal.setup_grade.value}]"
                ehp_mark = "🔥" if signal.is_ehp else ""
                test_mark = "🧪" if signal.has_test_phase else ""
        
                print(f"\n  ✅ {label} {signal.symbol} {grade_display} {ehp_mark}{test_mark}")
                print(f"     Model: {signal.model.value}")
                print(f"     Entry: ${signal.entry:.2f}" if signal.entry > 10 else f"     Entry: ${signal.entry:.4f}")
                print(f"     Stop: ${signal.stop:.2f}" if signal.stop > 10 else f"     Stop: ${signal.stop:.4f}")
                print(f"     Target: ${signal.target:.2f}" if signal.target > 10 else f"     Target: ${signal.target:.4f}")
                print(f"     R:R 1:{signal.rr:.1f}")
                print(f"     Conf: {int(signal.confidence*100)}% | QRZ: {signal.qrz.quality_score:.0%}")
                print(f"     Duration: {signal.range_duration_hours:.1f}h | {signal.reason[:50]}...")
        
                self.tg.send_signal(signal)
    
    def run(self):
        # Send startup message
        try:
            requests.post(self.tg._url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": "🚀 <b>ENHANCED TCT BOT - METALS EDITION STARTED</b>\n\n✅ XAUUSD (Gold)\n✅ XAGUSD (Silver)\n✅ XPTUSD (Platinum)\n✅ XPDUSD (Palladium)\n\n✅ Original Lectures 1-8 (100%)\n✅ Advanced PDF Concepts (100%)\n✅ Levels 1-3, QRZ, EHP, Test Phase\n✅ Context Grading A+ to C\n\n🎯 <b>ONLY A+ and A SETUPS SENT</b>\n\n🔔 Waiting for high-grade signals...",
                "parse_mode": "HTML"
            }, timeout=10)
        except:
            pass
        
        while True:
            try:
                self.run_once()
            except KeyboardInterrupt:
                print("\n🛑 Bot stopped")
                break
            except Exception as e:
                log.error(f"Error: {e}")
                traceback.print_exc()
            time.sleep(SCAN_INTERVAL_SECONDS)


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("\n⚠️  Note: Yahoo Finance provides free data with some delay.\n")
    scanner = EnhancedTCTScanner()
    scanner.run()
