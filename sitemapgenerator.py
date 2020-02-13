#!/usr/bin/env python
# coding: utf-8

# In[1]:


from urllib.request import urlopen, Request, HTTPError


# In[2]:


import urllib.parse as parse


# In[3]:


from datetime import datetime as dt


# In[4]:


import hashlib


# In[5]:


import re


# In[6]:


import csv


# In[37]:


class Robotstxt():
    def __init__(self,ssl=False):
        self.rules = {}
        self.sitemaps = []
        self.agents = []
        self.ssl = ssl
    def set_url(self,url):
        ad = 'https://' if self.ssl else 'http://' 
        text = urlopen(ad+url).read().decode('utf-8')
        cur = []
        self.rules['*'] = []
        agent = ''
        for line in text.split('\n'):
            if line.strip().lower().startswith('user-agent:'):#new agent
                #prev work
                if agent!='':
                    self.rules[agent] = self.rules.get(agent,[])+cur
                agent = line.strip().split(':')[1].strip()
            elif line.strip().lower().startswith('disallow:'):#new rule
                if len(line.strip().split(':')[1])!=0:
                    cur.append([False,line.strip().split(':')[1]])
                else:
                    cur.append([True,'/'])
            elif line.strip().lower().startswith('allow:'):
                if len(line.strip().split(':')[1])!=0:
                    cur.append([True,line.strip().split(':')[1]])
            elif line.strip().lower().startswith('Sitemap:'):
                if len(line.strip().split(':')[1])!=0:
                    self.sitemaps.append(line.strip().split(':')[1])
            else:#doesnt matter
                pass
        if agent!='':
            self.rules[agent] = self.rules.get(agent,[])+cur
        self.agents = [*self.rules]
    def can_fetch(self,agent,url):
        if agent!='*' and agent in self.agents:
            realrules = self.rules.get(agent,[])+self.rules.get('*',[])
        elif agent=='*':
            realrules = self.rules.get('*',[])
        elif agent not in self.agents:
            realrules = self.rules.get('*',[])
        else:
            realrules = self.rules.get('*',[])
        userules = sorted(realrules,key=lambda x:len(x[1].strip()),reverse=True)
        for rule in userules:
            crule = rule[1].strip()
            crule = crule.replace('*','.*')
            res = re.findall(crule,url)
            if len(res)>0:
                return rule[0]
        return True


# In[7]:


def getD(url):
    r= urlopen(Request(url, headers={'User-Agent': 'Mozilla'})).read()
    res = hashlib.md5(r)
    return r,res.hexdigest()


# In[26]:


def artd(ar):
    di = {}
    for i in ar:
        di[i[0]] = i[1]
    return di


# In[55]:


class Crawler():
    def __init__(self,host='http://example.com', debug=False):
        self.sitemap_lc = 1000 # link amount in one file
        self.sitemap_il = 'sitemap.xml'  # sitemap index main file name
        self.sitemap_fl = 'sitemap_{}.xml'# sitemap file pattern
        self.sitemap_hashkeep = 'hash{}.csv'.format('1') #name url hash keep
        ## local variables
        self.linksOnLook = [host]
        self.linksAlreadySaw = []
        self.linksAndHash = []
        self.debug = debug
        self.ssl = host.startswith('https')
        self.host = parse.urlparse(host).netloc
        self.td_str = dt.now().strftime('%d.%m.%Y')
    def linkLook(self,url):
        if self.debug:
            print('Parsing: {}'.format(url))
        try:
            res,hvalue = getD(url)
            page = str(res)
        except BaseException:
            if self.debug:
                print('some problems with link {}'.format(url))
                raise
            return None
        pattern = r'<a [^>]*href=[\'|"](.*?)[\'"].*?>'
        foundLinks = re.findall(pattern,page)
        links = []
        for link in foundLinks:
            if self.isUrl(link):
                if self.isInternal(link):
                    links.append(self.normalize(link))
        for link in links:
            curl = parse.urljoin(url,link)
            curl = self.normalize(curl)
            if curl not in self.linksAlreadySaw:
                self.linksAlreadySaw.append(curl)
                self.linksOnLook.append(curl)
        self.linksAndHash.append([url,hvalue])
            
    def normalize(self, url):
        scheme, netloc, path, qs, anchor = parse.urlsplit(url)
        return parse.urlunsplit((scheme, netloc, path, qs, anchor))
    
    def isUrl(self,url):
        scheme, netloc, path, qs, anchor = parse.urlsplit(url)
        if url != '' and scheme in ['http', 'https', '']:
            return True
        else:
            return False
        
    def isInternal(self,url):
        host = parse.urlparse(url).netloc
        return host == self.host or host == ''
    
    def start(self):
        fl = len(self.linksOnLook)>0
        while fl:# we have some links on look
            url = self.linksOnLook.pop(0)
            self.linksAlreadySaw.append(url)
            self.linkLook(url)
            fl = len(self.linksOnLook)>0
            print(len(self.linksOnLook))
        #already saw all links
        newd = self.checkUpdate()
        if len(newd)>0:
            self.save(newd)
    def saveHash(self,newst):
        d =artd(self.linksAndHash)
        with open(self.sitemap_hashkeep,'w') as f:
            for i in newst:
                try:
                    f.write('{};{};{}\n'.format(i[0],i[1],d.get(i[0],'None')))
                except BaseException:
                    print(i)
        #not finished
    def save(self,newst):
        self.saveHash(newst)
        self.linksForSitemap = self.leftOnlyGood()
        self.createSitemap()
        
    def createSitemap(self):
        lpatt = '<url><loc>{url}</loc>\n<lastmod>{lastmod}</lastmod>\n<priority>1.0</priority>\n</url>'
        ress = """<?xml version="1.0" encoding="UTF-8"?>
        <!-- 	created with seo-plus.ru/asdream	 --><urlset xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9 http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd">
            {document_list}
            </urlset>
             """
        ps = ''
        for item in self.linksForSitemap:
            n = lpatt.format(url=item[0],lastmod=dt.strptime(item[1],'%d.%m.%Y').strftime('%Y-%m-%d'))
            ps+=n+'\n'
        ans = ress.format(document_list=ps)
        with open(self.sitemap_il,'w') as file:
            file.write(ans)
        return True
    def leftOnlyGood(self):
        rb = Robotstxt(ssl=self.ssl)
        rb.set_url(self.host+'/robots.txt')
        l = []
        goodlink = []
        with open(self.sitemap_hashkeep,'r') as file:
            rr = csv.reader(file,delimiter=';')
            for i in rr:
                l.append([i[0],i[1],i[2]])
        for link,dat,ha in l:
            y = rb.can_fetch('Yandex',link)
            g = rb.can_fetch('Googlebot',link)
            if y and g:#link left
                goodlink.append([link,dat])
        return goodlink
    def checkUpdate(self):
        with open(self.sitemap_hashkeep,'r') as f:
            csvr = csv.reader(f,delimiter=';')
            dr = {}
            for line in csvr:
                dr[line[0]] = [line[1],line[2]]
            ans = []
            for link in self.linksAndHash:
                info = dr.get(link[0],-1)
                if (info !=-1) and (info[0] == link[1]):
                    ans.append(info)
                else:
                    ans.append(link[:1]+[self.td_str])
            return ans


# In[56]:


crw = Crawler(host='https://a.ru/',debug=False)
crw.start()

