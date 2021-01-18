"""
Script to analyze browsing history from Google Takeout: https://takeout.google.com/settings/takeout
"""

import io
import json
import os
from urllib.parse import urlparse

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HISTORY_FILEPATH = "inputs/history.json"


class GoogleHistoryAnalyzer:

    history_list_filepath = "exports/history_list.json"

    def __init__(self, single_page_time_spent_limit=600):
        self.single_page_time_spent_limit = single_page_time_spent_limit

        # write parsed version of history
        with open(HISTORY_FILEPATH, "r") as f:
            history_list = json.load(f)["Browser History"]
            with open(self.history_list_filepath, "w") as f:
                f.write(json.dumps(history_list))

        with open(self.history_list_filepath, "r") as f:
            self.df = pd.read_json(f, orient="records")

        # create datetime column
        self.df["timestamp"] = pd.to_datetime(self.df["time_usec"], unit="us")

    def process(self):

        # extract domains and subdomains from url
        self.df["domain_full"] = self.df.url.apply(lambda url: urlparse(url).netloc)

        def simple_domain(domain_full):
            parts = domain_full.split(".")
            if len(parts) > 2:
                return ".".join(parts[1:])
            else:
                return ".".join(parts)

        self.df["domain"] = self.df.domain_full.apply(lambda domain_full: simple_domain(domain_full))

        # drop domain == 'newtab'
        self.df = self.df[self.df.domain != "newtab"]

        # get month column
        self.df["month"] = pd.DatetimeIndex(self.df["timestamp"]).month
        self.df["year"] = pd.DatetimeIndex(self.df["timestamp"]).year

        # get time diff between rows (for minutes add .div(60))
        self.df["time_spent_s"] = -(self.df.timestamp.diff() / np.timedelta64(1, "s"))

        # upperbound seconds at 600 (10 minutes) [default] on a single page
        self.df.time_spent_s = self.df.time_spent_s.clip(upper=self.single_page_time_spent_limit)

        # derive from seconds
        self.df["time_spent_m"] = self.df["time_spent_s"] / 60
        self.df["time_spent_h"] = self.df["time_spent_m"] / 60
        self.df["time_spent_d"] = self.df["time_spent_h"] / 24

        # create seconds bins
        second_bins = [0, 1, 5, 10, 30, 60, 240, 600, 1800, np.inf]
        self.df["time_spent_bins"] = pd.cut(self.df.time_spent_s, second_bins)

    def time_by_domain(self, domains=None, subdomains=None, groupby="domain", include_month=False):

        # copy df
        _df = self.df.copy()

        # filter by domain
        if domains is not None:
            _df = _df[_df.domain.isin(domains)]

        # filter by subdomain
        if subdomains is not None:
            _df = _df[_df.domain_full.isin(subdomains)]

        # groupby domain
        groupby_cols = [groupby]
        if include_month:
            groupby_cols.insert(0, "month")
            groupby_cols.insert(1, "year")
        gp = _df.groupby(groupby_cols)

        # sum
        df = gp[["time_spent_s", "time_spent_m", "time_spent_h", "time_spent_d"]].sum()

        # sort by desc
        if include_month:
            df = df.sort_values(["year", "month", "time_spent_s"], ascending=[True, True, False])
        else:
            df = df.sort_values("time_spent_s", ascending=False)

        # return
        return df
