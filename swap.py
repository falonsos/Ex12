from datetime import date, timedelta

class Swap:
    """Representa un swap de tasas de interés simple."""

    def __init__(self, start_date: date, end_date: date,
                 frequency_months: int, notional: float, rate: float,
                 leg1_currency: str, leg2_currency: str,
                 fixed_leg: int = 1, float_leg: int = 2,
                 pay_leg: int = 1, receive_leg: int = 2,
                 float_spread: float = 0.0):
        self.start_date = start_date
        self.end_date = end_date
        self.frequency_months = frequency_months
        self.notional = notional
        self.rate = rate
        self.leg1_currency = leg1_currency
        self.leg2_currency = leg2_currency
        self.fixed_leg = fixed_leg
        self.float_leg = float_leg
        self.pay_leg = pay_leg
        self.receive_leg = receive_leg
        self.float_spread = float_spread

    # Helper to add months without external libraries
    @staticmethod
    def _add_months(d: date, months: int) -> date:
        year = d.year + (d.month - 1 + months) // 12
        month = (d.month - 1 + months) % 12 + 1
        day = min(d.day, [31,
                          29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                          31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month-1])
        return date(year, month, day)

    def coupon_dates(self):
        dates = [self.start_date]
        d = self.start_date
        while d < self.end_date:
            d = self._add_months(d, self.frequency_months)
            dates.append(min(d, self.end_date))
        return dates

    def year_fraction(self, d1: date, d2: date) -> float:
        return (d2 - d1).days / 360.0

    def fixed_leg_flows(self):
        dates = self.coupon_dates()
        flows = []
        for i in range(1, len(dates)):
            accrual = self.year_fraction(dates[i-1], dates[i])
            amount = self.notional * self.rate * accrual
            flows.append((dates[i], amount))
        return flows

    def floating_leg_flows(self, forward_curve):
        dates = self.coupon_dates()
        flows = []
        for i in range(1, len(dates)):
            accrual = self.year_fraction(dates[i-1], dates[i])
            fwd_rate = forward_curve.get(dates[i], self.rate)
            amount = self.notional * (fwd_rate + self.float_spread) * accrual
            flows.append((dates[i], amount))
        return flows

    def discount_curve(self, zero_rate: float):
        dates = self.coupon_dates()[1:]
        curve = {}
        for d in dates:
            t = self.year_fraction(self.start_date, d)
            df = 1 / (1 + zero_rate * t)
            curve[d] = df
        return curve

    def present_value(self, zero_rate: float, forward_curve):
        dcurve = self.discount_curve(zero_rate)
        fixed_flows = self.fixed_leg_flows()
        float_flows = self.floating_leg_flows(forward_curve)
        pv_fixed = sum(amt * dcurve[dt] for dt, amt in fixed_flows)
        pv_float = sum(amt * dcurve[dt] for dt, amt in float_flows)
        # Leg orientation
        pv_pay = pv_fixed if self.pay_leg == self.fixed_leg else pv_float
        pv_receive = pv_float if self.receive_leg == self.float_leg else pv_fixed
        return pv_receive - pv_pay
