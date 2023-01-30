import discord
from random import SystemRandom
from discord.ext import commands

## Discord's black circle emoji. Represents an open space.
open = ":black_circle:"

class GameBoard:
    def __init__(self, p1, p2):
        ## Essentially creates a 6 x 7 grid for the game.
        self.board = [[open, open, open, open, open, open, open],
                      [open, open, open, open, open, open, open],
                      [open, open, open, open, open, open, open],
                      [open, open, open, open, open, open, open],
                      [open, open, open, open, open, open, open],
                      [open, open, open, open, open, open, open]]

        ## Randomizes who goes first. Whoever gets ":red_circle:" goes first.
        if SystemRandom().randint(0, 1):
            self.players = {":red_circle:": p1, ":blue_circle:": p2}
        else:
            self.players = {":red_circle:": p2, ":blue_circle:": p1}

        self.red_turn = True
        
    def can_play(self, player):
        """Checks whose turn it is.
        
        Args:
            player (str): The player whose turn it is
            
        Returns:
            True: If it is that player's turn, False if it's the other player's.
        """
        if self.red_turn:
            return player == self.players[":red_circle:"]
        else:
            return player == self.players[":blue_circle:"]

    def check_column(self, column):
        """Checks the column to make sure that it's not full.
        
        Args:
            column [int]: Given column to drop a piece
            
        Returns:
            True: If the column is full, False if not.
        """
        for i in range(len(self.board)):
            if self.board[i][column] == open:
                ## Column is not full
                return False
        ## Column is full
        return True
    
    def check_spaces(self):
        """Checks all locations on the board for empty spaces.
        
        Returns:
            True: If the board is full, False if any open spaces are left.
        """
        for rows in self.board:
            if open in rows:
                ## Means the board is not full.
                return False
        ## Board is full.
        return True
    
    def drop(self, column):
        """Adds the player's piece to the selected column, if it's valid.
        
        Args:
            column (int): The column to drop the piece into.
            
        Returns:
            True: If the drop was sucessful, False if unsucessful
        """
        ## If it's red's turn, then place a red piece, otherwise place a blue one.
        if self.red_turn:
            piece = ':red_circle:'
        else:
            piece = ':blue_circle:'
            
        for i in range(len(self.board[column - 1])):
            ## We only want to drop one piece in the lowest available space.
            ## So we start from the bottom of the board and return immediately.
            if self.board[i][column] == open:
                self.board[i][column] = piece
                break
        else:
            return False
        
        ## If placing piece was sucessful, changes whose turn it is.
        self.red_turn = not self.red_turn
        return True
    
    def check_board(self):
        """Checks the board for any winning combinations.
        
        Returns:
            True: If there is a winning combination in any direction, False
            if there are no combintations.
        """
        board = self.board
        ## Check horizontal spaces (rows) from bottom to top
        for c in range(5):
            for r in range(3):
                if board[r][c] == board[r+1][c] == board[r+2][c] == board[r+3][c] and board[r][c] != open:
                    return self.players[board[r][c]]
        
        ## Check vertical spaces (columns) from left to right.
        for c in range(3):
            for r in range(2):
                if board[r][c] == board[r+1][c] == board[r+2][c] == board[r+3][c] and board[r][c] != open:
                    return self.players[board[r][c]]
        
        ## Check diagonal spaces in the positive direction.
        for c in range(3):
            for r in range(2):
                if board[r][c] == board[r+1][c+1] == board[r+2][c+2] == board[r+3][c+3] and board[r][c] != open:
                    return self.players[board[r][c]]

        ## Check diagonal spaces in the negative direction. 
        for c in range(3):
            for r in range(5):
                if board[r][c] == board[r-1][c+1] == board[r-2][c+2] == board[r-3][c+3] and board[r][c] != open:
                    return self.players[board[r][c]]

        ## No winning combinations.
        return None
    
    def __str__(self):
        """Returns string representation of the current game board."""
        ## Create the board, with open spaces denoted by a black circle.
        _board = (
        (F" {self.board[5][0]}{self.board[5][1]}{self.board[5][2]}{self.board[5][3]}{self.board[5][4]}{self.board[5][5]}{self.board[5][6]}\n") + 

        (F" {self.board[4][0]}{self.board[4][1]}{self.board[4][2]}{self.board[4][3]}{self.board[4][4]}{self.board[4][5]}{self.board[4][6]}\n") +

        (F" {self.board[3][0]}{self.board[3][1]}{self.board[3][2]}{self.board[3][3]}{self.board[3][4]}{self.board[3][5]}{self.board[3][6]}\n") +

        (F" {self.board[2][0]}{self.board[2][1]}{self.board[2][2]}{self.board[2][3]}{self.board[2][4]}{self.board[2][5]}{self.board[2][6]}\n") + 

        (F" {self.board[1][0]}{self.board[1][1]}{self.board[1][2]}{self.board[1][3]}{self.board[1][4]}{self.board[1][5]}{self.board[1][6]}\n") +

        (F" {self.board[0][0]}{self.board[0][1]}{self.board[0][2]}{self.board[0][3]}{self.board[0][4]}{self.board[0][5]}{self.board[0][6]}"))
        return (F"\n{_board}")

class ConnectFour(commands.Cog):
    ## Dictionary to store all running instances of the game, from different guilds.
    boards = {}
    
    def create(self, server_id, p1, p2):
        """Creates an instance of the GameBoard class.
        
        Args: 
            server_id (int): ID of the guild that is running on
            p1 (int): ID of player 1, who started the game
            p2 (int): ID of player 2, who was challenged to play
            
        Returns:
            first_turn: The player whose letter will be "X". This player always goes first.
        """
        self.boards[server_id] = GameBoard(p1, p2)
        ## Return who is "red", i.e. who is going first.
        first_turn = self.boards[server_id].players[":red_circle:"]
        return first_turn
    
    @commands.group(aliases=["drop", "column"], invoke_without_command=True)
    @commands.guild_only()
    async def connect_four(self, ctx, *, column: int):
        """Checks to make sure that given column exists, and that it's not full.
        If a valid location is given, then continues the game until the board is full or
        one of the players gets a winning combination.
        
        If the board is full and no one has a winning comination, then it is a tie.
        Both outcomes will also stop the instance of the game, so a new one can start.
        
        Args:
            column (int): Given column to drop a piece
            
        Returns:
            None: If an occupied, or non-existent space is given.
        """
        player = ctx.message.author
        board = self.boards.get(ctx.message.guild.id)

        ## Make sure that the board exists, i.e. a game is running on that guild.
        if not board:
            await ctx.send("There are currently no games running!")
            return

        ## Make sure that it is that player's turn.
        ## Prevent player "X" from going during "O"s turn, and the reverse.
        ## Also stop any random member from messing with the game.
        if not board.can_play(player):
            await ctx.send("You cannot play right now!")
            return

        ## Check to make sure that the column exists.
        if not 1 <= column <= 7:
            await ctx.send("Column must be a number from one to seven!")
            return
        
        ## Check if the column is full. If so, then request a different column.
        column -= 1
        column_full = board.check_column(column)
        if column_full:
            await ctx.send("That column is full. Please choose a different one.")
            return

        ## Drop piece into the selected column.
        if not board.drop(column):
            await ctx.send("That column is full. Please choose a different one.")
            return

        ## Check if there is a winner yet.
        winner = board.check_board()
        if winner:
            ## If loser is "red", then winner is "blue", and vice versa.
            if board.players[":red_circle:"] != winner:
                loser = board.players[":red_circle:"]
            else:
                loser = board.players[":blue_circle:"]
            
            win_msg = (F"{winner.display_name} has won! Sounds like {loser.display_name} has a skill issue.")
            win_embed = discord.Embed(title=win_msg, description=str(board))
            await ctx.send(embed=win_embed)
            ## End the game, so a new one can start.
            try:
                del self.boards[ctx.message.guild.id]
            except KeyError:
                pass
            
        else:
            ## If all spaces are full, and there are no winning combinations, it's a tie.
            if board.check_spaces():
                tie_msg = "A tie!\n"
                tie_embed = discord.Embed(title=tie_msg, description=str(board))
                tie_embed.set_footer(text="I suppose you both are equally bad.")
                await ctx.send(embed=tie_embed)
                
                try:
                    del self.boards[ctx.message.guild.id]
                except KeyError:
                    pass
            else:
                ## If no one has won yet, then alert whose turn it is and keep going.
                if board.red_turn:
                    player_turn = board.players.get(":red_circle:")
                else:
                    player_turn = board.players.get(":blue_circle:")
                
                turn_msg = (F"{player_turn.display_name}, it's now your turn!\n")
                turn_embed = discord.Embed(title=turn_msg, description=(F"{str(board)}"))
                await ctx.send(embed=turn_embed)

    @commands.command(name="connectfour")
    @commands.guild_only()
    async def start_connect_four(self, ctx, p2: discord.Member):
        """Starts a game of Connect Four and prints the game board.
        
        Args:
            p2 [discord.Member]: The member of the guild who was challenged to play
        
        Returns:
            None: If there is already a running game, or if there is an
            invalid target (either the bot or the player themself).
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
        
        #### If the member challenges themself.
        ##if p1 == p2:
        ##    await ctx.send("Please find some friends")
        ##    return

        ## Create the board and return who is "red", and will go first.
        red_player = self.create(ctx.message.guild.id, p1, p2)
        
        ## Announce that the game has started, print the board and who goes first.
        start_msg = (F"A game of connect four has started between {p1.display_name} and {p2.display_name}!\n")
        start_board = str(self.boards[ctx.message.guild.id])
        start_embed = discord.Embed(title=start_msg, description=start_board)
        start_embed.set_footer(text=(F"\nBy pure skill, I have decided that {red_player.display_name} will go first!"))
        await ctx.send(embed=start_embed)
        
    @commands.command(name="stopgame", aliases=["remove", "end"])
    @commands.guild_only()
    async def stop_game(self, ctx):
        """Stops the currently running game, if there is one."""
        if self.boards.get(ctx.message.guild.id) is None:
            await ctx.send("There are no games running right now.")
            return
        
        del self.boards[ctx.message.guild.id]
        await ctx.send("Looks like connect four will connect no more.")

## Add cog to the bot.
def setup(bot):
    bot.add_cog(ConnectFour(bot))