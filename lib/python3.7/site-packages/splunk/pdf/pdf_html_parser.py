from builtins import object
from lxml import etree
from copy import copy

class PdfHtmlParser(object):
    def __init__(self):
        # a list storing HTML fragments
        self.fragments = []
    
    def parse(self, html):
        root = etree.fromstring(html)
        
        while root is not None:
            (firstHalf, img, secondHalf) = self.split(root)
            self.fragments.append(firstHalf)
            if img is None:
                break
            else:
                self.fragments.append(img)
                img = None
                root = secondHalf
        
        return self.fragments
        
    def split(self, tree):
        """Split the HTML tree into two sub trees, separated by 
        the first img element (depth first search order of the tree) in the tree.
        A tuple (firstHalf, img, secondHalf) is returned.
        If there is not img element in the tree, 
        only the first element in the tuple will be populated. For example:
        <html><h1>before</h1><img src="test.png"/><h1>after</h1></html>
        This tree will be separated into three parts 
        (two subtrees with the img as separator):
        ('<h1>before</h1>', '<img src="test.png"/>', '<h1>after</h1>')
        """
        firstHalf = etree.Element(tree.tag)
        firstHalf.text = tree.text and tree.text
        firstHalf.tail = tree.tail and tree.tail
        secondHalf = None
        img = None
        for child in tree:
            if img is not None:
                if secondHalf is None:
                    secondHalf = etree.Element(tree.tag)
                secondHalf.append(child)
            elif child.tag == 'img':
                img = child
                if img.tail:
                    if secondHalf is None:
                        secondHalf = etree.Element(tree.tag)
                    secondHalf.text = img.tail
            else:
                (subFirstHalf, img, subSecondHalf) = self.split(child)
                firstHalf.append(subFirstHalf)
                if subSecondHalf is not None:
                    if secondHalf is None:
                        secondHalf = etree.Element(tree.tag)
                    secondHalf.append(subSecondHalf)
                
        return (firstHalf, img, secondHalf)
