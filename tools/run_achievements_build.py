#!/usr/bin/env python3
"""Compatibility runner for the staged achievements build."""

import build_achievements_update as builder


builder.TEMPLATE_CONTENT_ANCHOR = (
    '<h4 class="midashi3 mb30_md50">'
    "<?php echo $target['title'];?></h4>"
)

builder.build()
