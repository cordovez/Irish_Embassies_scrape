# Irish Embassies and Consulates Abroad
A personal project intended as an exercise in designing and creating databases from raw data collected from a web source.

**NB: The information may not be accurate and it is intended only as an educational tool.**

The data is scraped from the Irish Department of Foreign Affairs, Irish Embassies and Consulates Abroad.

This page does not have a very clear taxonomy and may be a work in progress. Therefore the css selectors used in this scraper may change eventually.

I have created private class methods in the spider, which reveal clearly how I am identifying the values taken an how they are processed. I found this more evident than using Item Loaders.

Because this information does not change significantly more than once or twice a year, I have decided not to automate it or host it with a third party. 

Finally, I used a proxy from [ScrapeOps](https://scrapeops.io/) to bypass a HTTP 401 response.