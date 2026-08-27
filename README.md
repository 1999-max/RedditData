# RedditData

## Personal Read-Only Reddit Research Tool

RedditData is a personal Python-based research project that uses Reddit's official Data API to retrieve a limited amount of publicly available Reddit content for research and analysis.

The application is read-only and does not perform automated interactions with Reddit users.

## Purpose

The purpose of this project is to review and organize publicly available Reddit discussions related to selected research topics.

The application searches a limited number of posts from specifically selected public subreddits and retrieves a limited number of public comments associated with those posts.

## Data Access

The application only accesses publicly available Reddit content, including:

* Public post titles
* Public post text
* Public comments
* Subreddit names
* Post and comment IDs
* Public timestamps
* Public score and engagement metadata

The application does not intentionally collect or store Reddit usernames.

## Access Scope

The tool is intentionally restricted to a small and clearly defined scope.

It:

* Searches only selected public subreddits
* Does not search all of Reddit
* Limits the number of posts retrieved for each search query
* Limits the number of comments retrieved from each post
* Does not access private or restricted Reddit content
* Uses Reddit's official OAuth Data API through PRAW
* Operates in read-only mode

The source code contains additional safeguards that prevent unrestricted collection.

## What This Tool Does Not Do

The application does not:

* Create Reddit posts
* Submit comments
* Vote or change votes
* Send private messages
* Follow users
* Moderate communities
* Access private messages
* Access private subreddits
* Collect authentication credentials from Reddit users
* Attempt to identify individual Reddit users
* Build user profiles
* Infer sensitive characteristics about Reddit users
* Sell Reddit data
* Redistribute Reddit data as a dataset
* Provide Reddit data to third parties
* Train AI or machine-learning models using Reddit data

## Data Storage

Retrieved information is stored locally on the developer's computer for personal research and analysis.

The collected data is not exposed through a public service or API and is not redistributed to third parties.

Local research data should be deleted when it is no longer necessary for the stated research purpose.

## Rate Limits and Responsible Usage

This application is designed to respect Reddit's API rules and rate limits.

The application intentionally limits:

* The number of subreddits that may be queried
* The number of posts retrieved per query
* The number of comments retrieved per post
* Expansion of additional comment trees

The project will comply with Reddit's applicable Developer Terms, Data API Terms, Responsible Builder Policy, and API rate limits.

## Authentication

OAuth credentials are not stored in this public repository.

After Reddit API access is approved, the following values must be configured locally:

* Reddit Client ID
* Reddit Client Secret
* Reddit User Agent

Real API credentials must never be committed to GitHub.

## Technology

* Python 3
* PRAW
* Reddit OAuth Data API

## Project Status

This repository currently represents the read-only application prototype submitted as part of a Reddit Data API access request.

API credentials will only be added locally after Reddit grants access.
