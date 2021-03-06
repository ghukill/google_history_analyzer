"""
Script to analyze browsing history from Google Takeout: https://takeout.google.com/settings/takeout
"""

import argparse
import json
import logging
import os
import random
from urllib.parse import urlparse
import uuid

import numpy as np
import pandas as pd

logging.getLogger().setLevel(logging.INFO)


# setup some interactive pandas settings
pd.options.display.max_rows = 500
pd.options.display.max_colwidth = 100


class GoogleHistoryAnalyzer:

    """
    Client class to analyze download Google Chrome history
    """

    history_list_filepath = "exports/history_list.json"

    default_domain_clip_time_spent = 600

    # TODO: include regex for urls, not just domain (e.g. foo.com/longplay/abc123 vs foo.com/settings)
    custom_domain_clip_time_spent = {
        "meet.google.com": 10800,
        "youtube.com": 3600,
        "netflix.com": 10800,
        "hulu.com": 10800,
    }

    def __init__(self, input_filepath="inputs/history.json"):

        self.input_filepath = input_filepath

        # if ./exports directory does not exist, attempt to create
        if not os.path.exists("./exports"):
            try:
                os.mkdir("exports")
            except:
                raise Exception("could not created directory: ./exports")

        # write parsed version of history
        logging.info(f"parsing input: {self.input_filepath}")
        with open(self.input_filepath, "r") as f:
            history_list = json.load(f)["Browser History"]
            with open(self.history_list_filepath, "w") as f:
                f.write(json.dumps(history_list))

        with open(self.history_list_filepath, "r") as f:
            self.df = pd.read_json(f, orient="records")

        logging.info(f"parsed {len(self.df)} history entries")

    def process(self):

        """
        Extract, synthesize, and normalize columns for analysis
        """

        logging.info("pre-processing data for analysis")

        # create datetime column
        self.df["timestamp"] = pd.to_datetime(self.df["time_usec"], unit="us")

        # extract domains and subdomains from url
        self.df["domain_full"] = self.df.url.apply(lambda url: urlparse(url).netloc)
        self.df["domain"] = self.df.domain_full.apply(lambda domain_full: self.simple_domain(domain_full))

        # drop domain == 'newtab'
        logging.debug("dropping 'newtab' entries")
        self.df = self.df[self.df.domain != "newtab"]

        # get month column
        self.df["month"] = pd.DatetimeIndex(self.df["timestamp"]).month
        self.df["year"] = pd.DatetimeIndex(self.df["timestamp"]).year

        # get earliest and latest date
        self.first_date = self.df.iloc[0].timestamp
        self.last_date = self.df.iloc[-1].timestamp

        # get time diff between rows (for minutes add .div(60))
        self.df["time_spent_s"] = -(self.df.timestamp.diff() / np.timedelta64(1, "s"))

        # upperbound seconds at 600 (10 minutes) [default] on a single page
        self.clip_time_spent()

        # derive from seconds
        self.df["time_spent_m"] = self.df["time_spent_s"] / 60
        self.df["time_spent_h"] = self.df["time_spent_m"] / 60
        self.df["time_spent_d"] = self.df["time_spent_h"] / 24

        # create seconds bins
        second_bins = [0, 1, 5, 10, 30, 60, 240, 600, 1800, 3600, np.inf]
        self.df["time_spent_bins"] = pd.cut(self.df.time_spent_s, second_bins)

    @classmethod
    def simple_domain(cls, domain_full):

        """
        rough approximation of domain
        """

        parts = domain_full.split(".")
        if len(parts) == 1:
            return domain_full
        elif len(parts) == 2:
            return ".".join(parts)
        elif len(parts) > 2:
            return ".".join(parts[1:])

    def date_filter_df(self, df, date_start=None, date_end=None, copy=True):

        """
        Filter dataframe by date ranges

        :param date_start: str, date lower bound (e.g. '2020-06-01' or '2020-06-01 00:13:05')
        :param date_end: str, date upper bound (e.g. '2020-06-01' or '2020-06-01 00:13:05')
        """

        if copy:
            _df = df.copy()

        # lower bound
        if date_start is not None:
            df = df[df.timestamp >= date_start]

        # upper bound
        if date_end is not None:
            df = df[df.timestamp <= date_end]

        # return df
        return df

    def clip_time_spent(self):

        """
        Method to set upper bound for time spent on page
        """

        # loop through and perform custom clips
        for domain, upper_bound in self.custom_domain_clip_time_spent.items():
            self.df.loc[self.df.domain == domain, "time_spent_s"] = self.df[self.df.domain == domain].time_spent_s.clip(
                upper=upper_bound
            )

        # clip all non-custom domains to 10 minutes
        self.df.loc[~self.df.domain.isin(list(self.custom_domain_clip_time_spent.keys())), "time_spent_s"] = self.df[
            ~self.df.domain.isin(list(self.custom_domain_clip_time_spent.keys()))
        ].time_spent_s.clip(upper=self.default_domain_clip_time_spent)

    def time_by_domain(
        self,
        domains=None,
        subdomains=None,
        groupby="domain",
        include_month=False,
        date_start=None,
        date_end=None,
        export=None,
    ):

        """
        Method to analyze by time spent on domains

        :param domains: filter by "simple" domain (e.g. mail.google.com --> google.com)
        :param subdomains: filter by full domain from urlparse.netloc
        :param groupby: str, "domain" or "subdomain"
        :param include_month: boolean, if True include month/year in groupby cols
        :param date_start: datetime, lower bound on date
        :param date_end: datetime, upper bound on date
        """

        # copy df
        _df = self.df.copy()

        # apply date filters
        _df = self.date_filter_df(_df, date_start=date_start, date_end=date_end, copy=False)

        # filter by domain
        if domains is not None:
            _df = _df[_df.domain.isin(domains)]

        # filter by subdomain
        if subdomains is not None:
            _df = _df[_df.domain_full.isin(subdomains)]

        # setup groupby columns
        groupby_cols = [{"domain": "domain", "subdomain": "domain_full"}[groupby]]

        # if breakdown by month, add to groupby cols
        if include_month:
            groupby_cols.insert(0, "month")
            groupby_cols.insert(1, "year")
        gp = _df.groupby(groupby_cols)

        # sum time spent
        df = gp[["time_spent_s", "time_spent_m", "time_spent_h", "time_spent_d"]].sum()

        # sort by desc
        if include_month:
            df = df.sort_values(["year", "month", "time_spent_s"], ascending=[True, True, False])
        else:
            df = df.sort_values("time_spent_s", ascending=False)

        # return or export
        if export is not None:
            self.export_df(df, export)
        else:
            return df

    def time_by_random_domain(self, export=None, **kwargs):

        """
        Method to analyze by time spent on domains

        :param groupby: str, "domain" or "subdomain"
        :param include_month: boolean, if True include month/year in groupby cols
        :param date_start: datetime, lower bound on date
        :param date_end: datetime, upper bound on date
        """

        # get random domain from full data
        domains = self.df.domain.unique()
        random_domain = domains[random.randint(0, (len(domains) - 1))]

        # execute time_by_domain()
        return self.time_by_domain(domains=[random_domain], groupby="subdomain", include_month=True, export=export)

    def export_df(self, df, export_format):

        """
        Method to export analysis
        """

        # create random filename
        filename = f"exports/{str(uuid.uuid4())}.{export_format.lower()}"

        # csv
        if export_format == "csv":
            df.to_csv(filename)

        # tsv
        elif export_format == "tsv":
            df.to_csv(filename, sep="\t")

        # excel
        elif export_format == "xls":
            df.to_excel(filename)

        # console
        elif export_format == "console":
            df = df.reset_index()
            print(df.to_markdown(index=False))

        if export_format != "console":
            logging.info(f"exported file: {filename}, with {len(df)} rows")


def main(input_filepath, analysis, export, kwargs):

    # init client
    try:
        client = GoogleHistoryAnalyzer(input_filepath=input_filepath)

        # process
        client.process()

        # run analysis
        logging.info(f"running analysis method: {analysis}")
        analysis_func = getattr(client, analysis)
        analysis_func(export=export, **kwargs)

    except Exception as e:
        logging.error(str(e))


if __name__ == "__main__":

    # parse args
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis", default="time_by_domain")
    parser.add_argument("--export", default="console")
    parser.add_argument("--kwargs", default="{}")
    parser.add_argument("--input_filepath", default="inputs/history.json")

    # mix-ins for kwargs
    parser.add_argument("--domains", nargs="+", default=None)
    parser.add_argument("--subdomains", nargs="+", default=None)
    parser.add_argument("--groupby", default="domain")
    parser.add_argument("--include_month", default=False)
    parser.add_argument("--date_start", default=None)
    parser.add_argument("--date_end", default=None)

    args = parser.parse_args()

    # apply mixins
    kwargs = json.loads(args.kwargs)
    for arg in ["domains", "subdomains", "groupby", "include_month", "date_start", "date_end"]:
        kwargs[arg] = getattr(args, arg)

    # run main
    main(args.input_filepath, args.analysis, args.export, kwargs)
