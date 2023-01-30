import discord
from random import SystemRandom
import re

from discord.ext import commands

## Discord's black square emoji. Represents an open space.
square = ":black_large_square:"

class GameBoard:
    def __init__(self, p1, p2):
        ## Essentially creates a 3 x 3 grid for the game.
        self.board = [[square, square, square],
                      [square, square, square],
                      [square, square, square]]

        ## Randomize who goes first. Whoever gets ":x:" goes first.
        ## ":x:" is a red X, and ":o:" is a red O
        if SystemRandom().randint(0, 1):
            self.players = {":x:": p1, ":o:": p2}
        else:
            self.players = {":x:": p2, ":o:": p1}

        self.X_turn = True

    def check_all_space(self):
        """Checks all locations on the board for empty spaces.
        
        @return:
            True: If the board is full, False if any open spaces are left.
        """
        for rows in self.board:
            if square in rows:
                ## Means the board is not full.
                return False
            
        return True

    def can_play(self, player):
        """Checks whose turn it is.
        
        Args:
            player (str): The player whose turn it is
            
        Returns:
            True: If it is that player's turn, False if it's the other player's.
        """
        
        if self.X_turn:
            return player == self.players[":x:"]
        else:
            return player == self.players[":o:"]

    def update_board(self, x, y):
        """Updates the game board with the player's letter.
        
        Also switches to the other player's turn if the given space was valid.
        
        Args: 
            x (int): X location where the letter is placed.
            y (int): Y location where the letter is placed.
        
        Returns:
            True: If the letter was placed into an open space, False
            if it is occupied.
        """
        ## If it's player X's turn, then place an X, otherwise place an O.
        if self.X_turn:
            letter = ":x:"
        else:
            letter = ":o:"
            
        ## Check if the location has a space. If so then adds the letter.
        if self.board[x][y] == square:
            self.board[x][y] = letter
        else:
            return False

        ## If placing piece was sucessful, changes whose turn it is.
        self.X_turn = not self.X_turn
        return True

    def check_board(self):
        """Checks the board for any winning combinations.
        
        Returns:
            (str): A string representing a space on the board.
            None: If there are no winning combinations
        """
        ##-------------Horizontals-------------##
        ## Check the top row, from left to right.
        if (self.board[0][0] == self.board[0][1]
        and self.board[0][0] == self.board[0][2]
        and self.board[0][0] != square):
            return self.players[self.board[0][0]]
        
        ## Check middle row, from left to right.
        if (self.board[1][0] == self.board[1][1]
        and self.board[1][0] == self.board[1][2]
        and self.board[1][0] != square):
            return self.players[self.board[1][0]]

        ## Check bottom row, from left to right.
        if (self.board[2][0] == self.board[2][1]
        and self.board[2][0] == self.board[2][2]
        and self.board[2][0] != square):
            return self.players[self.board[2][0]]
        
        ##--------------Verticals--------------##
        ## Check left column, from top to bottom.
        if (self.board[0][0] == self.board[1][0]
        and self.board[0][0] == self.board[2][0]
        and self.board[0][0] != square):
            return self.players[self.board[0][0]]

        ## Check middle column, from top to bottom.
        if (self.board[0][1] == self.board[1][1] 
        and self.board[0][1] == self.board[2][1] 
        and self.board[0][1] != square):
            return self.players[self.board[0][1]]
        
        ## Check right column, from top to bottom.
        if (self.board[0][2] == self.board[1][2]
        and self.board[0][2] == self.board[2][2]
        and self.board[0][2] != square):
            return self.players[self.board[0][2]]
        
        ##--------------Diagonals--------------##
        ## Check diagonal, from top left to bottom right.
        if (self.board[0][0] == self.board[1][1]
        and self.board[0][0] == self.board[2][2]
        and self.board[0][0] != square):
            return self.players[self.board[0][0]]

        ## Check diagonal, from bottom left to top right.
        if (self.board[2][0] == self.board[1][1]
        and self.board[2][0] == self.board[0][2]
        and self.board[0][0] != square):
            return self.players[self.board[2][0]]

        ## No winning combinations.
        return None

    def __str__(self):
        """Returns string representation of the current game board."""
        ## Creates the board, with open spaces denoted by a black square.
        _board = (
        (F"{self.board[0][0]}{self.board[0][1]}{self.board[0][2]}\n") + 

        (F"{self.board[1][0]}{self.board[1][1]}{self.board[1][2]}\n") +

        (F"{self.board[2][0]}{self.board[2][1]}{self.board[2][2]}")
        )
        return (F"\n{_board}")


class TicTacToe(commands.Cog):
    ## Dictionary to store all running instances of the game, from different guilds.
    boards = {}

    def create(self, server_id, p1, p2):
        """Creates an instance of the GameBoard class.
        
        Args: 
            server_id (int): ID of the guild that is running on.
            p1 (int): ID of player 1, who started the game.
            p2 (int): ID of player 2, who was challenged to play.
            
        Returns:
            first_turn: The player whose letter will be ":x:". This player always goes first.
        """
        self.boards[server_id] = GameBoard(p1, p2)
        ## Return who is ":x:", i.e. who is going first.
        first_turn = self.boards[server_id].players[":x:"]
        return first_turn

    @commands.group(aliases=["tic", "tac", "toe", "ttt"], invoke_without_command=True)
    @commands.guild_only()
    async def tictactoe(self, ctx, *, option: str):
        """Searches the player's message for a valid location to play ":x:" or ":x:"
        If a valid location is given, then continues the game until the board is full or
        one of the players gets a winning combination.
        
        If the board is full and no one has a winning comination, then it is a tie.
        Both outcomes will also stop the instance of the game, so a new one can start.
        
        Args:
            option (str): The location that the player's piece will be placed.
            The valid locations are:
            
            Top, Bottom, Left, Right, and Middle.
            Top and bottom, and left and right are mutually exclusive and cannot be used together.
            Two options should be chosen at most.
            
        Returns:
            None: If an occupied, or non-existent space is given.
        """
        player = ctx.message.author
        board = self.boards.get(ctx.message.guild.id)

        ## Make sure that the board exists, i.e. a game is running on that guild.
        if not board:
            await ctx.send("There are currently no game running!")
            return

        ## Make sure that it is that player's turn.
        ## Prevent player ":x:" from going during ":x:"s turn, and the reverse.
        ## Also stop any random member from messing with the game.
        if not board.can_play(player):
            await ctx.send("You cannot play right now!")
            return

        ## Search the player's message for these options, just checks if it exists.
        top = re.search("top", option)
        middle = re.search("middle", option)
        bottom = re.search("bottom", option)
        left = re.search("left", option)
        right = re.search("right", option)

        ## Not possible to place a piece in both locations.
        if top and bottom:
            await ctx.send("That is not a valid location!")
            return
        
        if left and right:
            await ctx.send("That is not a valid location!")
            return

        ## If a valid location isn't given at all.
        if not top and not bottom and not left and not right and not middle:
            await ctx.send("Really? Don't be like that.")
            return
        
        x = 0
        y = 0

        ## Assignments for x and y.
        ## 0, 1, 2 represent top, middle, bottom row for y.
        ## 0, 1, 2 represent left, middle, right column for x.
        if top:
            x = 0
        if bottom:
            x = 2
        if left:
            y = 0
        if right:
            y = 2

        ## If only middle was given, then this is the center of the board.
        if middle and not (top or bottom or left or right):
            x = 1
            y = 1
        
        ## If just top or bottom were given, then top-middle or bottom-middle.
        if (top or bottom) and not (left or right):
            y = 1

        ## If just left or right were given, then left-middle or right middle.
        elif (left or right) and not (top or bottom):
            x = 1

        ## If that space already has a letter, does nothing.
        if not board.update_board(x, y):
            await ctx.send("Someone has already played a piece there!")
            return

        ## Check if there is a winner yet.
        winner = board.check_board()
        if winner:
            ## If loser is ":x:", then winner is ":x:", and vice versa.
            if board.players[":x:"] != winner:
                loser = board.players[":x:"]
            else:
                loser = board.players[":o:"]
            
            winner_msg = (F"{winner.display_name} has won!")
            loser_msg = (F"\nSounds like {loser.display_name} has a skill issue.")
            done_embed = discord.Embed(title=winner_msg, description=(F"{str(board)}\n{loser_msg}"))
            await ctx.send(embed=done_embed)
            ## End the game, so a new one can start
            try:
                del self.boards[ctx.message.guild.id]
            except KeyError:
                pass
            
        else:
            ## If all spaces are full, and there are no winning combinations, it's a tie.
            if board.check_all_space():
                tie_embed = discord.Embed(title="A tie!\n", description=str(board))
                tie_embed.set_footer(text="I suppose you both are equally bad.")
                await ctx.send(embed=tie_embed)
                try:
                    del self.boards[ctx.message.guild.id]
                except KeyError:
                    pass
            else:
                ## If no one has won yet, then alert whose turn it is and keep going.
                if board.X_turn:
                    player_turn = board.players.get(":x:")
                else:
                    player_turn = board.players.get(":o:")
                    
                turn_msg = (F"{player_turn.display_name}, it's now your turn!\n")
                turn_embed = discord.Embed(title=turn_msg, description=str(board))
                await ctx.send(embed=turn_embed)

    @commands.command(name="starttic", aliases=["challenge", "create"])
    @commands.guild_only()
    async def start_game(self, ctx, p2: discord.Member):
        """Starts a game of Tic-Tac-Toe.
        
        Args:
            p2 (discord.Member): The member of the guild who was challenged to play
        
        @return:
            None: If there is already a running game, or if there is an
            invalid target (either the bot or the player themself)
        """
        p1 = ctx.message.author
        
        ## Only one game per server, else things would get pretty complicated.
        if self.boards.get(ctx.message.guild.id) is not None:
            await ctx.send("Only one game can run at a time!")
            return

        ## If the member challenges the bot. Very offensive.
        if p2 == ctx.message.guild.me:
            await ctx.send("Oh, so you're challenging me? Very well. I win!")
            return
        
        ## If the member challenges themself.
        ##if p1 == p2:
        ##    await ctx.send("Please find some friends")
        ##    return
        
        ## Create the board and return who is ":x:", and will go first.
        x_player = self.create(ctx.message.guild.id, p1, p2)
        
        ## Announce that the game has started, print the board and who goes first.
        start_msg = (F"A game of tic-tac-toe has started between {p1.display_name} and {p2.display_name}!\n")
        start_board = str(self.boards[ctx.message.guild.id])
        start_embed = discord.Embed(title=start_msg, description=start_board)
        start_embed.set_footer(text=(F"\nBy pure skill, I have decided that {x_player.display_name} will go first!"))
        await ctx.send(embed=start_embed)

    @tictactoe.command(name="stopttt", aliases=["remove", "end"])
    @commands.guild_only()
    async def stop_game(self, ctx):
        """Stops the currently running game, if there is one."""
        if self.boards.get(ctx.message.guild.id) is None:
            await ctx.send("There are no games running right now.")
            return
        
        del self.boards[ctx.message.guild.id]
        await ctx.send("Looks like tic-tac-toe has become tic-tac-no")

## Add cog to the bot.
def setup(bot):
    bot.add_cog(TicTacToe(bot))