;;; -*- lexical-binding: t -*-
;; Allow for macOS (dev machine) & Linux (GitHub Actions) execution
(defvar site-lisp-base 
  (if (eq system-type 'darwin)
      "~/.config/emacs/.local/straight/repos"               ; macOS path
    "/home/linuxbrew/.config/emacs/.local/straight/repos")) ; CI/Linux path

;; Explicitly load packages
(add-to-list 'load-path (expand-file-name "htmlize" site-lisp-base))
(add-to-list 'load-path (expand-file-name "weblorg" site-lisp-base))
(add-to-list 'load-path (expand-file-name "templatel" site-lisp-base))

(require 'htmlize)
(require 'weblorg)

;; Set default URL for Weblorg
;; Only works if environment variable ENV=prod
(if (string-equal-ignore-case (getenv "ENV") "prod")
    (setq weblorg-default-url "https://cleberg.net"))

;; Define site metadata
(weblorg-site
 :theme nil
 :template-vars '(("site_name"        . "cleberg.net")
                  ("site_owner"       . "Christian Cleberg <hello@cleberg.net>")
                  ("site_description" . "Just a blip of ones and zeroes.")))

;; Define routes for rendering content

;; Index page route
(weblorg-route
 :name "index"
 :input-pattern "content/*.org"
 :template "index.html"
 :output ".build/index.html"
 :url "/")

;; Blog post route
(weblorg-route
 :name "blog"
 :input-pattern "content/blog/*.org"
 :template "post.html"
 :output ".build/blog/{{ slug }}.html"
 :url "/blog/{{ slug }}.html")

;; Blog index page route
(weblorg-route
 :name "blog-index"
 :input-pattern "content/blog/*.org"
 :input-aggregate #'weblorg-input-aggregate-all-desc
 :template "blog.html"
 :output ".build/blog/index.html"
 :url "/blog/")

;; Page post route
(weblorg-route
 :name "pages"
 :input-pattern "content/*.org"
 :template "page.html"
 :output ".build/{{ slug }}.html"
 :url "/{{ slug }}.html")

;; Salary page route
(weblorg-route
 :name "salary"
 :input-pattern "content/salary/*.org"
 :template "page.html"
 :output ".build/salary/{{ slug }}.html"
 :url "/salary/{{ slug }}.html")

;; Services page route
(weblorg-route
 :name "services"
 :input-pattern "content/services/*.org"
 :template "page.html"
 :output ".build/services/{{ slug }}.html"
 :url "/services/{{ slug }}.html")

;; Now page route
(weblorg-route
 :name "now"
 :input-pattern "content/now/*.org"
 :template "post.html"
 :output ".build/now/{{ slug }}.html"
 :url "/now/{{ slug }}.html")

;; About page route
(weblorg-route
 :name "about"
 :input-pattern "content/about/*.org"
 :template "page.html"
 :output ".build/about/{{ slug }}.html"
 :url "/about/{{ slug }}.html")

;; Uses page route
(weblorg-route
 :name "uses"
 :input-pattern "content/uses/*.org"
 :template "page.html"
 :output ".build/uses/{{ slug }}.html"
 :url "/uses/{{ slug }}.html")

;; Tips page route
(weblorg-route
 :name "tips"
 :input-pattern "content/tips/*.org"
 :template "page.html"
 :output ".build/tips/{{ slug }}.html"
 :url "/tips/{{ slug }}.html")

;; RSS feed route
(weblorg-route
 :name "rss"
 :input-pattern "content/blog/*.org"
 :input-aggregate #'weblorg-input-aggregate-all-desc
 :template "feed.xml"
 :output ".build/feed.xml"
 :url "/feed.xml")

;; Copy static assets and output to .build directory
(weblorg-copy-static
 :output ".build/{{ file }}"
 :url "/{{ file }}")

;; Export all content using Weblorg engine
(weblorg-export)
