import datetime 

class Temperature:

    def __init__(self, high, low, date):
        self.high = high
        self.low = low
        self.date = date

    def get_high(self):
        return self.high

    def get_low(self):
        return self.low

    def get_date(self):
        return self.date
    def get_icon(self):
        return self.icon
    def get_detailed_forecast(self):
        return self.detailed_forecast

    def set_values(self, high, low, date, icon, detailed_forecast):
        self.high = high
        self.low = low
        self.date = date
        self.icon = icon
        self.detailed_forecast = detailed_forecast

    def get_month_day(self):
        dt = self.date
        md = f'{dt:%B} {dt.day}'
        return md
