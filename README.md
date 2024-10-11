# TestSys2PCMS

TestSys log to PCMS XMLs converter.

## Usage

Install [Python 3.8+](https://www.python.org/downloads/).

Install Python packages: `pip3 install requests requests_file`.

Run: `python testsys2pcms.py [config.yaml]`.

## Examples

Local file
    * [Configuration](examples/20100117.yaml)
    * Command `python testsys2pcms.py examples/20100117.yaml`

Downloading from URL
    * [Configuration](examples/m240512.yaml)
    * Command `python testsys2pcms.py examples/m240512.yaml`

Downloading from URL with all options
    * [Configuration](examples/m240512-full.yaml)
    * Command `python testsys2pcms.py examples/m240512-full.yaml`
