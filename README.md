# Google History analyzer

## Known Shortcomings

  * websites where "consuming" might be opening a tab and listening / watching content will have durations only until another browsing action is performed
    * e.g. 30 video watched on `youtube.com`, but navigated to `foo.com` 5 minutes in, duration for domain `youtube.com` will be only 5 minutes for that interaction

## Instructions

1. Download browsing history from Google Takeout

2. Find JSON file with the good stuff in it, and copy to `./inputs/history.json`

3. create python virtual environment
```
python3.7 -m venv venv
```

4. activate the virtual environment
```
source venv/bin/activate
```

5. pip install requirements
```
pip install -r requirements.txt
```

6. run ipython shell
```
ipython
```

7. import class and process for fun stuff
```python
from google_history import *

# init, which parses history as dataframe
gha = GoogleHistoryAnalyzer()

# process history to get some time diffs and whatnot
gha.process()
```

## Usage

### standalone executable binary

Somewhat experimental, this python script has been packaged as mac binary that can be executed standalone.

#### Installation

  1. create a new, dedicated directory to work in
  2. download [mac binary](https://github.com/ghukill/google_history_analyzer/releases/download/0.1/google_history) there
  3. create `inputs` directory and move Google Takeout history JSON file into that directory
  4. test by analyzing random domain:

```bash
./google_history --analysis time_by_random_domain
``` 

#### example: search for time spent on two domains broken down by month, output to screen

```
./google_history --domains github.com stackoverflow.com --include_month true
```

#### example: single domain, broken down by subdomain, for date range, output to screen

```
./google_history --domains google.com --groupby subdomain --date_start 06-01-2020 --date_end 07-01-2020
```

#### example: ALL domains, exported to CSV file (potentially large)

```
./google_history --export csv
```

### python library

Analyze time spent on a domain by month:
```python
# single domain
In [7]: gha.time_by_domain(domains=['github.com'], include_month=True)
Out[7]: 
                        time_spent_s  time_spent_m  time_spent_h  time_spent_d
month year domain                                                             
1     2020 github.com   37949.766548    632.496109     10.541602      0.439233
2     2020 github.com   92134.818560   1535.580309     25.593005      1.066375
3     2020 github.com  148657.930982   2477.632183     41.293870      1.720578
4     2020 github.com  126811.410246   2113.523504     35.225392      1.467725
5     2020 github.com  125543.230470   2092.387174     34.873120      1.453047
6     2020 github.com  137417.492970   2290.291550     38.171526      1.590480
7     2020 github.com   96113.521105   1601.892018     26.698200      1.112425
8     2020 github.com   51225.053362    853.750889     14.229181      0.592883
9     2020 github.com   95776.239536   1596.270659     26.604511      1.108521
10    2020 github.com   62318.492835   1038.641547     17.310692      0.721279
11    2020 github.com   41983.558352    699.725973     11.662100      0.485921
12    2020 github.com   68817.253327   1146.954222     19.115904      0.796496
1     2021 github.com   20499.244154    341.654069      5.694234      0.237260

# optionally group by subdomains
In [8]: gha.time_by_domain(domains=['google.com'], groupby='domain_full', include_month=True)
Out[8]: 
                                time_spent_s  time_spent_m  time_spent_h  time_spent_d
month year domain_full                                                                
1     2020 mail.google.com      23903.218449    398.386974      6.639783      0.276658
           www.google.com       17106.307148    285.105119      4.751752      0.197990
           docs.google.com      16501.604543    275.026742      4.583779      0.190991
           calendar.google.com  12129.222970    202.153716      3.369229      0.140385
           photos.google.com     2014.755217     33.579254      0.559654      0.023319
...                                      ...           ...           ...           ...
      2021 one.google.com          58.431027      0.973850      0.016231      0.000676
           contacts.google.com     37.831374      0.630523      0.010509      0.000438
           store.google.com        28.769666      0.479494      0.007992      0.000333
           scholar.google.com      15.685013      0.261417      0.004357      0.000182
           groups.google.com       11.427065      0.190451      0.003174      0.000132

[237 rows x 4 columns]
```

## Building Standalone Executable

  * include `--onefile` to build single file executable

### Mac OS
```bash
pyinstaller google_history.py --onefile --noconfirm --clean --hidden-import cmath --hidden-import tabulate --exclude-module PIL --exclude-module IPython --exclude PyInstaller
```

## Running Standalone Executable

*TODO*