# coding: utf-8

from __future__ import unicode_literals

from django.db import models

# Create your models here.

class Blog(models.Model):
    u'''博客测试
    '''
    title = models.CharField(u'标题', max_length=100)
    content = models.TextField(u'正文', null=True, blank=True)
    add_dt = models.DateTimeField('添加时间', blank=True, null=True, auto_now_add=True)

    class Meta:
        verbose_name = "Blog"
        verbose_name_plural = "Blogs"

    def __unicode__(self):
        return self.title
    