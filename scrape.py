import os
import csv
import time
import json
import requests
import xlsxwriter

from bs4 import BeautifulSoup
from urllib.parse import urlparse


def get_page_soup(url, wait_time=1):
    """
        Returns the page at desired url, caching it for future reference
        under ./pages so we don't have to scrape it a second time.
    """
    page_name = urlparse(url)
    # Extract just the page name
    page_name = os.path.basename(page_name.path)
    # Remove the extension, and add back html (could be php)
    page_name = os.path.splitext(page_name)[0] + '.html'

    # If the page is in the cache, return it
    # Else scrape it
    if os.path.isfile(f"./pages/{page_name}"):
        file = open(f"./pages/{page_name}", mode='r', encoding='utf8')
        soup = BeautifulSoup(file, 'lxml')
    else:
        # Courtesy delay if we're scraping lots of file to not put too much load on the site
        # though it should be fine. Can also serve not to get blocked by automatic rules.
        time.sleep(wait_time)
        resp = requests.get(url)
        soup = BeautifulSoup(resp.text, 'lxml')
        # Save the page to the page for further reference
        with open(f"./pages/{page_name}", mode='w', encoding='utf8') as outfile:
            outfile.write(soup.prettify())

    return soup


def get_regions():
    """
        Returns all the regions along with links to their bottinsante page
    """
    # First page of the site
    soup = get_page_soup('https://www.bottinsante.ca/CHSLD-Quebec-1.html')

    all_regions = soup.find('div', class_='regions-wrap')
    all_columns = all_regions.find_all('div', class_='colonne')

    region_links = {}

    for column in all_columns:
        for p_region in column.find_all('p'):
            region_name = p_region.a.get_text().strip()
            region_page = p_region.a['href']
            region_links[region_name] = 'https://www.bottinsante.ca/' + region_page
    
    with open('data/regions.json', 'w', encoding='utf8') as outfile:
        json.dump(region_links, outfile, ensure_ascii=False)

    return region_links


def get_CHSLD_links():
    """
        For each region, fetch the list of CHSLDs and the links to their indexsante.ca page.
        We go to indexsante because it has a bit more information, including the postal code. 
    """
    if os.path.isfile('./data/regions.json'):
        region_links = json.load(open('./data/regions.json', 'r', encoding='utf8'))
    else:
        region_links = get_regions()

    CHSLD_links = {}

    for region, link in region_links.items():
        # Skip the whole of QC listing so we can associate region to each CHSLD
        if region == 'Tout le Québec':
            continue
        
        # Checked all the pages and none have more than 1 page (except for QC wide which we skip)
        soup = get_page_soup(link)

        entries = soup.find_all('div', class_='regulier')
        # Some entries have this classname 'base' and have less info, but still a link
        entries.extend(soup.find_all('div', class_='base'))
        
        for entry in entries:
            name = entry.a['title']
            link = entry.a['href']
            # Add the region as well, so we don't have to find it again after
            link_and_region = {
                'link': link,
                'region': region
            }
            CHSLD_links[name] = link_and_region
        
    with open('./data/CHSLDs.json', 'w', encoding='utf8') as outfile:
        json.dump(CHSLD_links, outfile, ensure_ascii=False)

    return CHSLD_links



def scrape_all_CHSLDs():
    """
        Scrape the CHSLD's indexsante.ca page for relevant information.
        Write out a CSV and Excel file containing the data.
    """
    if os.path.isfile('./data/CHSLDs.json'):
        CHSLD_links = json.load(open('./data/CHSLDs.json', 'r', encoding='utf8'))
    else:
        CHSLD_links = get_CHSLD_links()

    print("Scraping:")

    # We will hold a list of dictionaries with all the CHSLD info we care about
    CHSLD_info = []
    for name, link_and_region in CHSLD_links.items():
        info = {}
        info['name'] = name
        info['region'] = link_and_region['region']
        info['link'] = link_and_region['link']
        print(f"\t{info['link']}")

        soup = get_page_soup(link_and_region['link'])

        phone_div = soup.find('div', id='fiche-telephone-appeler')
        if phone_div:
            info['phone'] = phone_div.a.get_text().strip()
        else:
            info['phone'] = ''
        
        website_div = soup.find('div', id='fiche-web-url')
        if website_div:
            info['website'] = soup.find('div', id='fiche-web-url').a['href']
        else:
            info['website'] = ''

        address_block = soup.find('p', class_='adresse')

        address_parts = address_block.decode_contents().split('</strong>')[1:][0]
        address_parts = address_parts.split('<br/>')
        # Should have elements: street address, city, postal code
        address_parts = [ part.strip() for part in address_parts if part.strip() ]

        if len(address_parts) >= 3:
            info['address'] = address_parts[0]
            info['city'] = address_parts[1].replace('(Québec)', '').strip()
            info['postalcode'] = address_parts[2]
        else:
            print("\t\tProblem parsing address")

        CHSLD_info.append(info)
    
    # Write the CSV file
    header = ['Name', 'Region', 'Street Address', 'City', 'Postal Code', 'Phone Number', 'Website', 'Scraped Page']
    with open('CHSLDs.csv', 'w', newline='', encoding='utf8') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        csvwriter.writerow(header)

        for CHSLD in CHSLD_info:
            row = [CHSLD['name'], CHSLD['region'], CHSLD['address'], CHSLD['city'], CHSLD['postalcode'], CHSLD['phone'], CHSLD['website'], CHSLD['link']]
            csvwriter.writerow(row)

    # Write the Excel file
    try:
        with xlsxwriter.Workbook('CHSLDs.xlsx') as workbook:
            worksheet = workbook.add_worksheet()
            worksheet.write_row(0, 0, header)

            for i, CHSLD in enumerate(CHSLD_info):
                row = [CHSLD['name'], CHSLD['region'], CHSLD['address'], CHSLD['city'], CHSLD['postalcode'], CHSLD['phone'], CHSLD['website'], CHSLD['link']]
                worksheet.write_row(i+1, 0, row)

            num_cols = len(header)
            # Add filters on the top row
            worksheet.autofilter(0, 0, 0, num_cols-1)

    except xlsxwriter.exceptions.FileCreateError as e:
        print("Unable to open the excel file. Make sure it's not open on your computer!")
        print(e)



if __name__ == '__main__':
    # Create these two directories if they don't exist
    if not os.path.isdir('./pages'):
        os.mkdir('./pages')
    if not os.path.isdir('./data'):
        os.mkdir('./data')

    scrape_all_CHSLDs()