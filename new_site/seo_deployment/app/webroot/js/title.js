(function() {
setTimeout(title01, 10);
    function title01() {
        var scrollElemToWatch_1 = document.getElementById('title01');
        if (!scrollElemToWatch_1) return;
        var watcher_1 = scrollMonitor.create(scrollElemToWatch_1, -100),                
            rev1 = new RevealFx(scrollElemToWatch_1, {
                revealSettings : {
                    bgcolor: '#e7e7e7',
                    duration: 600,
                    onStart: function(contentEl, revealerEl) { 
                        anime.remove(contentEl);
                        contentEl.style.opacity = 0; 
                    },
                    onCover: function(contentEl, revealerEl) { 
                        contentEl.style.opacity = 1;
                        anime({
                            targets: contentEl,
                            duration: 100,
                            delay: 10,
                            easing: 'easeOutExpo',
                            opacity: [0,1]
                        });
                    }
                }
            })
        watcher_1.enterViewport(function() {
            rev1.reveal();
            watcher_1.destroy();
        });
    }
})();

(function() {
setTimeout(title02, 10);
    function title02() {
        var scrollElemToWatch_1 = document.getElementById('title02');
        if (!scrollElemToWatch_1) return;
        var watcher_1 = scrollMonitor.create(scrollElemToWatch_1, -100),                
            rev1 = new RevealFx(scrollElemToWatch_1, {
                revealSettings : {
                    bgcolor: '#e7e7e7',
                    duration: 600,
                    onStart: function(contentEl, revealerEl) { 
                        anime.remove(contentEl);
                        contentEl.style.opacity = 0; 
                    },
                    onCover: function(contentEl, revealerEl) { 
                        contentEl.style.opacity = 1;
                        anime({
                            targets: contentEl,
                            duration: 100,
                            delay: 10,
                            easing: 'easeOutExpo',
                            opacity: [0,1]
                        });
                    }
                }
            })
        watcher_1.enterViewport(function() {
            rev1.reveal();
            watcher_1.destroy();
        });
    }
})();


(function() {
setTimeout(title03, 10);
    function title03() {
        var scrollElemToWatch_1 = document.getElementById('title03');
        if (!scrollElemToWatch_1) return;
        var watcher_1 = scrollMonitor.create(scrollElemToWatch_1, -100),                
            rev1 = new RevealFx(scrollElemToWatch_1, {
                revealSettings : {
                    bgcolor: '#caedff',
                    duration: 600,
                    onStart: function(contentEl, revealerEl) { 
                        anime.remove(contentEl);
                        contentEl.style.opacity = 0; 
                    },
                    onCover: function(contentEl, revealerEl) { 
                        contentEl.style.opacity = 1;
                        anime({
                            targets: contentEl,
                            duration: 100,
                            delay: 10,
                            easing: 'easeOutExpo',
                            opacity: [0,1]
                        });
                    }
                }
            })
        watcher_1.enterViewport(function() {
            rev1.reveal();
            watcher_1.destroy();
        });
    }
})();


(function() {
setTimeout(title04, 10);
    function title04() {
        var scrollElemToWatch_1 = document.getElementById('title04');
        if (!scrollElemToWatch_1) return;
        var watcher_1 = scrollMonitor.create(scrollElemToWatch_1, -100),                
            rev1 = new RevealFx(scrollElemToWatch_1, {
                revealSettings : {
                    bgcolor: '#caedff',
                    duration: 600,
                    onStart: function(contentEl, revealerEl) { 
                        anime.remove(contentEl);
                        contentEl.style.opacity = 0; 
                    },
                    onCover: function(contentEl, revealerEl) { 
                        contentEl.style.opacity = 1;
                        anime({
                            targets: contentEl,
                            duration: 100,
                            delay: 10,
                            easing: 'easeOutExpo',
                            opacity: [0,1]
                        });
                    }
                }
            })
        watcher_1.enterViewport(function() {
            rev1.reveal();
            watcher_1.destroy();
        });
    }
})();


(function() {
    var banner = document.getElementById('banner1');
    if (!banner) return;
    banner.style.opacity = '1';
    banner.style.visibility = 'visible';
})();


(function() {
setTimeout(banner2, 10);
    function banner2() {
        var scrollElemToWatch_1 = document.getElementById('banner2');
        if (!scrollElemToWatch_1) return;
        var watcher_1 = scrollMonitor.create(scrollElemToWatch_1, -100),                
            rev1 = new RevealFx(scrollElemToWatch_1, {
                revealSettings : {
                    bgcolor: '#212125',
                    duration: 600,
					direction: 'rl',/*右から左*/
                    onStart: function(contentEl, revealerEl) { 
                        anime.remove(contentEl);
                        contentEl.style.opacity = 0; 
                    },
                    onCover: function(contentEl, revealerEl) { 
                        contentEl.style.opacity = 1;
                        anime({
                            targets: contentEl,
                            duration: 100,
                            delay: 10,
                            easing: 'easeOutExpo',
                            opacity: [0,1]
                        });
                    }
                }
            })
        watcher_1.enterViewport(function() {
            rev1.reveal();
            watcher_1.destroy();
        });
    }
})();


(function() {
setTimeout(banner3, 10);
    function banner3() {
        var scrollElemToWatch_1 = document.getElementById('banner3');
        if (!scrollElemToWatch_1) return;
        var watcher_1 = scrollMonitor.create(scrollElemToWatch_1, -100),                
            rev1 = new RevealFx(scrollElemToWatch_1, {
                revealSettings : {
                    bgcolor: '#212125',
                    duration: 600,
					/*direction: 'rl',右から左*/
                    onStart: function(contentEl, revealerEl) { 
                        anime.remove(contentEl);
                        contentEl.style.opacity = 0; 
                    },
                    onCover: function(contentEl, revealerEl) { 
                        contentEl.style.opacity = 1;
                        anime({
                            targets: contentEl,
                            duration: 100,
                            delay: 10,
                            easing: 'easeOutExpo',
                            opacity: [0,1]
                        });
                    }
                }
            })
        watcher_1.enterViewport(function() {
            rev1.reveal();
            watcher_1.destroy();
        });
    }
})();



(function() {
setTimeout(banner4, 10);
    function banner4() {
        var scrollElemToWatch_1 = document.getElementById('banner4');
        if (!scrollElemToWatch_1) return;
        var watcher_1 = scrollMonitor.create(scrollElemToWatch_1, -100),                
            rev1 = new RevealFx(scrollElemToWatch_1, {
                revealSettings : {
                    bgcolor: '#212125',
                    duration: 600,
					/*direction: 'rl',右から左*/
                    onStart: function(contentEl, revealerEl) { 
                        anime.remove(contentEl);
                        contentEl.style.opacity = 0; 
                    },
                    onCover: function(contentEl, revealerEl) { 
                        contentEl.style.opacity = 1;
                        anime({
                            targets: contentEl,
                            duration: 100,
                            delay: 10,
                            easing: 'easeOutExpo',
                            opacity: [0,1]
                        });
                    }
                }
            })
        watcher_1.enterViewport(function() {
            rev1.reveal();
            watcher_1.destroy();
        });
    }
})();
