base_prompt = """
As the scraping agent, extract and format the following values into a JSON object:
{}.

#######################################

1. If 'type', 'section', or 'subsection' appear, extract values for each distinct type/section/subsection as specified in the context.
2. Ensure the JSON is valid and correctly formatted.
3. Combine values with same keys.
4. Extract and include the article's author and publication date if present in the text, else NA.
5. Maintain consistent key structure for nested values or list of objects. If 1st object in list has keys 'a' and 'b', all objects in list should have it.
6. Ignore CSS and javascript elements, focus on the main content/helpful html elements like class names and alt texts only.
7. Don't make nested structures, keep json as flat as possible.
8. Make sure data types are appropriate. Eg: author, title should be text, multiple values on page should be list, key values should be dictionaries.
9. If there are multiple values for something, keep the most probable value 1st.


Example:

EXAMPLE INPUT:
<time datetime="2018-12-15">Dec 15, 2018</time>
<p>Published by: <img src="/asdas/asdasd/lvj.jpg" alt="john doe">
<div>Published on: 29th May</div>
<div class="quest"><p>what is this thing? ... \n</p> <p>ksdnf <u>kjn<\\u> skndfk jksfd ...</p></div>
<div class="answers"><ul><li>this is a pen</li>\n<li> This is ldf ... sdf ... \n ... sdfsdfkjskf\n</li></div>

EXAMPLE OUTPUT:
{{
    "author": "john doe",
    "time": "Dec 15, 2018",
    "published_date": "29th May",
    "question": "what is this thing? ... \n ksdnf kjn skndfk jksfd ..."
    "answers": ["this is a pen", " This is ldf ... sdf ... \n ... sdfsdfkjskf\n"]
}}
"""


get_tags_prompt = """
From these list of tags and classes, mention which tag and class might contain some information related to {}. Here are the tags:
{}
########################################
The values should exist in the original input. Response should contain only the key values and be formatted as:

Example:

INPUT:
tag:class1 class2 class3
tag2:class1 class4 class5
tag4:class9 class1

OUTPUT:
key_name1:tag:class1 class2 class3
key_name1:tag4:class9 class1
key_name3:tag4:class9 class1
"""